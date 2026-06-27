import time

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemoryItem,
    MemoryItemKind,
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
)
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from openai.types.responses import ResponseInputParam
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemoryStoreEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    foundry_project_endpoint: str
    memory_store_chat_model_deployment_name: str
    memory_store_embedding_model_deployment_name: str


options = MemoryStoreDefaultOptions(
    chat_summary_enabled=True,
    user_profile_enabled=True,
    procedural_memory_enabled=True,
    default_ttl_seconds=30 * 24 * 60 * 60,
    user_profile_details="Avoid irrelevant or sensitive data, such as age, financials, precise location, and credentials",  # noqa E501
)


class MemoryStore:
    def __init__(self, app_id: str):
        env = MemoryStoreEnv()  # type: ignore
        self.project_client = AIProjectClient(
            endpoint=env.foundry_project_endpoint,
            credential=DefaultAzureCredential(),
        )
        definition = MemoryStoreDefaultDefinition(
            chat_model=env.memory_store_chat_model_deployment_name,
            embedding_model=env.memory_store_embedding_model_deployment_name,
            options=options,
        )
        self.name = f"{app_id}-memory-store"
        # Memories are scoped per user as "{tenant_id}_{app_id}_{user_id}" to
        # match the scope MyAgent uses when reading/writing them.

        try:
            self.memory_store = self.project_client.beta.memory_stores.get(
                name=self.name
            )
        except ResourceNotFoundError:
            self.memory_store = self.project_client.beta.memory_stores.create(
                name=self.name,
                definition=definition,
                description="Memory store with 30-day default TTL",
            )

    def remember(self, user_id: str, items: str | ResponseInputParam) -> None:
        """Persist a message or conversation to memory deterministically.

        Pass a plain string for a single note, or a list of
        ``{"role", "type": "message", "content"}`` dicts to store a
        user-assistant exchange. Only items with ``type == "message"`` are
        processed; others are ignored by the memory extractor.

        Relying on the agent tool's asynchronous, inactivity-based extraction is
        best-effort and may store nothing for short messages. This forces an
        immediate, synchronous memory update (update_delay=0) and waits for it to
        complete, so the next conversation can reliably search it.
        """
        poller = self.project_client.beta.memory_stores.begin_update_memories(
            name=self.name,
            scope=user_id,
            items=items,
            update_delay=0,  # Trigger update immediately without waiting
        )
        poller.result()  # Wait until memories are extracted and stored

    def list_memories(
        self, user_id: str, kind: MemoryItemKind | None = None
    ) -> list[MemoryItem]:
        scope = user_id
        return self._list_memories_with_retry(scope, kind=kind)

    def clear_memory(
        self, user_ids: list[str], passes: int = 3, delay: float = 5.0
    ) -> None:
        # The list/search index is eventually consistent, so a single pass may
        # miss memories that aren't indexed yet. Re-list and delete a few times,
        # pausing between passes to let the index catch up, until it reports empty.
        for user_id in user_ids:
            for attempt in range(passes):
                # The preview memory-store API occasionally returns a transient 500,
                # so materialize the page (rather than deleting while paging) before
                # deleting each memory.
                memories = self._list_memories_with_retry(user_id)
                if not memories:
                    return
                for memory in memories:
                    self.project_client.beta.memory_stores.delete_memory(
                        name=self.name, memory_id=memory.memory_id
                    )
                if attempt < passes - 1:
                    time.sleep(delay)

    def _list_memories_with_retry(
        self, scope: str, attempts: int = 3, kind: MemoryItemKind | None = None
    ) -> list[MemoryItem]:
        for attempt in range(attempts):
            try:
                return list(
                    self.project_client.beta.memory_stores.list_memories(
                        name=self.name, scope=scope, kind=kind
                    )
                )
            except HttpResponseError:
                if attempt == attempts - 1:
                    raise
                time.sleep(2 * (attempt + 1))
        return []  # pragma: no cover - loop always returns or raises
