import json
import time

from azure.ai.projects.models import MemoryItemKind

from azure_ai_memory_store.myagent import MyAgent
from azure_ai_memory_store.services.memory_store import MemoryStore

user_id = "john_doe"

MSG_SOCCER = [
    "I am rooting for England to win the World Cup.",
    "I am referring to the Soccer World Cup, not the Rugby World Cup.",
    "I am a big fan of the England national football team since I was a child.",
]

MSG_COFFEE = [
    "I love coffee.",
    "I prefer my coffee black, without sugar or milk.",
    "I usually drink coffee in the morning to help me wake up.",
]

MSG_AZURE = [
    "What is the pricing model for Azure OpenAI Service?",
    "Does it support pay-as-you-go or subscription-based pricing?",
    "Are there any free tiers or trial options available for developers?",
]


def init_memory_store() -> None:
    # Ensure the memory store exists before the agent references it.
    MemoryStore().clear_memory(user_id=user_id)
    # Deletes are eventually consistent: the memory search index lags behind
    # delete_memory, so pause to let it catch up before the next chat.
    time.sleep(5)


def chat_with_agent(agent: MyAgent, messages: list[str]) -> None:
    conversation_id: str | None = None

    for message in messages:
        print("Sending message to agent:", message)
        response, conversation_id = agent.chat(
            user_id=user_id, message=message, conversation_id=conversation_id
        )
        print("Response:", response.output_text)


def sleep_for_memory_extraction() -> None:
    # The MemorySearchPreviewTool extracts memories from the conversation
    # automatically after `update_delay` seconds of inactivity. Wait for that
    # asynchronous extraction to complete before starting a new conversation.
    print("\nWaiting for memories to be stored...\n")
    time.sleep(65)


def ask_agent_about_memories(agent: MyAgent) -> None:
    message = "Do you know the team that I am supporting for the World Cup."
    print("Sending message to agent:", message)
    response, _ = agent.chat(user_id=user_id, message=message)
    print("Response:", response.output_text)

    data = MemoryStore().list_memories(
        user_id=user_id, kind=MemoryItemKind.CHAT_SUMMARY
    )
    print(json.dumps([m.as_dict() for m in data], indent=2, default=str))


def main() -> None:
    init_memory_store()

    agent_client = MyAgent()
    chat_with_agent(agent_client, MSG_SOCCER)
    chat_with_agent(agent_client, MSG_COFFEE)
    chat_with_agent(agent_client, MSG_AZURE)
    sleep_for_memory_extraction()
    ask_agent_about_memories(agent_client)


if __name__ == "__main__":
    main()
