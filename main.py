import json
import time

from azure.ai.projects.models import MemoryItemKind

from azure_ai_memory_store.myagent import MyAgent
from azure_ai_memory_store.services.memory_store import MemoryStore

USER_JOHN_DOE = "john_doe"
USER_MARY_ANN = "mary_ann"

APP_ID = "faq-bot"

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

MSG_FOOD = [
    "I love Italian food, especially pasta and pizza.",
    "I enjoy trying new recipes and experimenting with different ingredients.",
    "I often cook at home and like to host dinner parties for friends and family.",
]


def init_memory_store(app_id: str) -> None:
    # Ensure the memory store exists before the agent references it.
    MemoryStore(app_id).clear_memory([USER_JOHN_DOE, USER_MARY_ANN])
    # Deletes are eventually consistent: the memory search index lags behind
    # delete_memory, so pause to let it catch up before the next chat.
    time.sleep(5)


def chat_with_agent(agent: MyAgent, user_id: str, messages: list[str]) -> None:
    conversation_id: str | None = None

    for message in messages:
        print(f"Sending message to agent from {user_id}:", message)
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


def _ask_agent_about_memories(agent: MyAgent, user_id: str, question: str) -> None:
    print(f"Sending question to agent from {user_id}:", question)
    response, _ = agent.chat(user_id=user_id, message=question)
    print("Response:", response.output_text)


def ask_agent_about_memories(agent: MyAgent) -> None:
    _ask_agent_about_memories(
        agent,
        USER_JOHN_DOE,
        "Do you know the team that I am supporting for the World Cup.",
    )
    print("\n")

    _ask_agent_about_memories(
        agent,
        USER_MARY_ANN,
        "Do you know the team that I am supporting for the World Cup.",
    )
    print("\n")

    _ask_agent_about_memories(
        agent,
        USER_MARY_ANN,
        "Do you know if I like Italian food or not.",
    )

    for user_id in [USER_JOHN_DOE, USER_MARY_ANN]:
        print(f"\nListing memories for user {user_id}:")
        data = MemoryStore(APP_ID).list_memories(
            user_id=user_id, kind=MemoryItemKind.CHAT_SUMMARY
        )
        print(json.dumps([m.as_dict() for m in data], indent=2, default=str))
        print("\n")


def main() -> None:
    init_memory_store(APP_ID)

    agent_client = MyAgent(APP_ID)

    # user john_doe sends a series of messages to the agent, which are stored in the
    # memory store
    for messages in [MSG_SOCCER, MSG_COFFEE, MSG_AZURE]:
        chat_with_agent(agent_client, USER_JOHN_DOE, messages)

    # user mary_ann sends messages to the agent, which are stored in the
    # memory store
    chat_with_agent(agent_client, USER_MARY_ANN, MSG_FOOD)

    sleep_for_memory_extraction()

    # john should only be able to see his own memories
    # and mary should only be able to see her own memories
    ask_agent_about_memories(agent_client)


if __name__ == "__main__":
    main()
