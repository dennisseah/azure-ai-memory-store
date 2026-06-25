import time

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
)
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from pydantic_settings import BaseSettings, SettingsConfigDict


class MemoryStoreEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    foundry_project_endpoint: str
    memory_store_chat_model_deployment_name: str
    memory_store_embedding_model_deployment_name: str
    tenant_id: str
    app_id: str


options = MemoryStoreDefaultOptions(
    chat_summary_enabled=True,
    user_profile_enabled=True,
    procedural_memory_enabled=True,
    default_ttl_seconds=30 * 24 * 60 * 60,
    user_profile_details="Avoid irrelevant or sensitive data, such as age, financials, precise location, and credentials",  # noqa E501
)


class MemoryStore:
    def __init__(self):
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
        self.name = env.tenant_id + "-" + env.app_id + "-memory-store"
        # Memories are scoped per user as "{tenant_id}_{app_id}_{user_id}" to
        # match the scope MyAgent uses when reading/writing them.
        self.scope_prefix = f"{env.tenant_id}_{env.app_id}"
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

    def clear_memory(self, user_id: str):
        scope = f"{self.scope_prefix}_{user_id}"
        # The preview memory-store API occasionally returns a transient 500, so
        # materialize the page (rather than deleting while paging) and retry a
        # few times before giving up.
        memories = self._list_memories_with_retry(scope)
        for memory in memories:
            self.project_client.beta.memory_stores.delete_memory(
                name=self.name, memory_id=memory.memory_id
            )

    def _list_memories_with_retry(self, scope: str, attempts: int = 3):
        for attempt in range(attempts):
            try:
                return list(
                    self.project_client.beta.memory_stores.list_memories(
                        name=self.name, scope=scope
                    )
                )
            except HttpResponseError:
                if attempt == attempts - 1:
                    raise
                time.sleep(2 * (attempt + 1))
        return []  # pragma: no cover - loop always returns or raises
