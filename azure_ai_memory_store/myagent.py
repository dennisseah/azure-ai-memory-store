from functools import lru_cache

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    AgentVersionDetails,
    MemorySearchPreviewTool,
    PromptAgentDefinition,
)
from azure.identity import DefaultAzureCredential
from openai.types.responses import Response
from pydantic_settings import BaseSettings, SettingsConfigDict


class MyAgentEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    foundry_project_endpoint: str
    memory_store_chat_model_deployment_name: str
    tenant_id: str
    app_id: str


class MyAgent:
    def __init__(self):
        env = MyAgentEnv()  # type: ignore
        self.project_client = AIProjectClient(
            endpoint=env.foundry_project_endpoint,
            credential=DefaultAzureCredential(),
        )

        # Scope may only contain A-Z, a-z, 0-9, '-', and '_' (no '/').
        self.scope = f"{env.tenant_id}_{env.app_id}"
        self.env = env

    def _scope(self, user_id: str) -> str:
        return f"{self.scope}_{user_id}"

    def _memory_store_name(self) -> str:
        return f"{self.env.tenant_id}-{self.env.app_id}-memory-store"

    def remember(self, user_id: str, message: str) -> None:
        """Persist a message to memory deterministically.

        Relying on the agent tool's asynchronous, inactivity-based extraction is
        best-effort and may store nothing for short messages. This forces an
        immediate, synchronous memory update (update_delay=0) and waits for it to
        complete, so the next conversation can reliably search it.
        """
        poller = self.project_client.beta.memory_stores.begin_update_memories(
            name=self._memory_store_name(),
            scope=self._scope(user_id),
            items=message,
            update_delay=0,  # Trigger update immediately without waiting
        )
        poller.result()  # Wait until memories are extracted and stored

    @lru_cache
    def _create_agent(self, user_id: str) -> AgentVersionDetails:
        scope = self._scope(user_id)
        memory_store_name = self._memory_store_name()

        tool = MemorySearchPreviewTool(
            memory_store_name=memory_store_name,
            scope=scope,
            update_delay=1,  # Wait 1 second of inactivity before updating memories
        )
        return self.project_client.agents.create_version(
            agent_name="MyAgent",
            definition=PromptAgentDefinition(
                model=self.env.memory_store_chat_model_deployment_name,
                instructions=(
                    "You are a helpful assistant that answers general questions"
                ),
                tools=[tool],
            ),
        )

    def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> tuple[Response, str]:
        openai_client = self.project_client.get_openai_client()
        agent = self._create_agent(user_id=user_id)

        if conversation_id is None:
            conversation = openai_client.conversations.create()
            conversation_id = conversation.id

        response = openai_client.responses.create(
            input=message,
            conversation=conversation_id,
            extra_body={
                "agent_reference": {"name": agent.name, "type": "agent_reference"}
            },
        )

        return (response, conversation_id)

    def close_conversation(self, conversation_id: str | None) -> None:
        if conversation_id is None:
            return
        openai_client = self.project_client.get_openai_client()
        openai_client.conversations.delete(conversation_id)
