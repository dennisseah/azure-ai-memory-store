from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MemorySearchPreviewTool
from azure.identity import DefaultAzureCredential
from openai.types.responses import Response
from pydantic_settings import BaseSettings, SettingsConfigDict


class MyAgentEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    foundry_project_endpoint: str
    memory_store_chat_model_deployment_name: str


class MyAgent:
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.memory_store_name = f"{self.app_id}-memory-store"

        env = MyAgentEnv()  # type: ignore
        self.project_client = AIProjectClient(
            endpoint=env.foundry_project_endpoint,
            credential=DefaultAzureCredential(),
        )
        self.env = env

    def chat(
        self,
        user_id: str,
        message: str,
        conversation_id: str | None = None,
    ) -> tuple[Response, str]:
        openai_client = self.project_client.get_openai_client()

        if conversation_id is None:
            conversation = openai_client.conversations.create()
            conversation_id = conversation.id

        tool = MemorySearchPreviewTool(
            memory_store_name=self.memory_store_name,
            scope=user_id,
            update_delay=1,  # Wait 1 second of inactivity before updating memories
        )

        response = openai_client.responses.create(
            model=self.env.memory_store_chat_model_deployment_name,
            input=message,
            conversation=conversation_id,
            instructions=("You are a helpful assistant that answers general questions"),
            tools=[tool],  # type: ignore[list-item]
        )

        return (response, conversation_id)

    def close_conversation(self, conversation_id: str | None) -> None:
        if conversation_id is None:
            return
        openai_client = self.project_client.get_openai_client()
        openai_client.conversations.delete(conversation_id)
