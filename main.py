import json
import time

from azure.ai.projects.models import MemoryItemKind

from azure_ai_memory_store.myagent import MyAgent
from azure_ai_memory_store.services.memory_store import MemoryStore

USER_JOHN_DOE = "john_doe"
USER_MARY_ANN = "mary_ann"

APP_FAQ_1 = "faq-bot_1"
APP_FAQ_2 = "faq-bot_2"


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
]

MSG_ITALIAN_FOOD = [
    "I love Italian food, especially pasta and pizza.",
    "I enjoy trying new recipes and experimenting with different ingredients.",
]


def init_memory_store() -> None:
    # Ensure the memory store exists before the agent references it.
    for app_id in [APP_FAQ_1, APP_FAQ_2]:
        MemoryStore(app_id).clear_memory([USER_JOHN_DOE, USER_MARY_ANN])
    # Deletes are eventually consistent: the memory search index lags behind
    # delete_memory, so pause to let it catch up before the next chat.
    time.sleep(5)


def chat_with_agent(agent: MyAgent, user_id: str, messages: list[str]) -> None:
    conversation_id: str | None = None

    for message in messages:
        print(f"Sending message to {agent.app_id} from {user_id}:", message)
        response, conversation_id = agent.chat(
            user_id=user_id, message=message, conversation_id=conversation_id
        )
        print("Response:", response.output_text)
        time.sleep(5)  # Wait for the MemorySearchPreviewTool to extract memories


def sleep_for_memory_extraction() -> None:
    # The MemorySearchPreviewTool extracts memories from the conversation
    # automatically after `update_delay` seconds of inactivity. Wait for that
    # asynchronous extraction to complete before starting a new conversation.
    print("\nWaiting for memories to be stored...\n")
    time.sleep(200)


def _ask_agent_about_memories(agent: MyAgent, user_id: str, question: str) -> bool:
    print(f"Sending question to {agent.app_id} from {user_id}:", question)
    response, _ = agent.chat(user_id=user_id, message=question)
    print("Response:", response.output_text)
    print("\n")
    return False if response.output_text == "do not know" else True


def ask_agent_about_memories(
    agent: MyAgent, questions: list[tuple[str, str]]
) -> list[bool]:
    return [
        _ask_agent_about_memories(
            agent,
            user_id,
            f"{question}\nPlease answer with 'do not know' and nothing else if you do not know.",  # noqa: E501
        )
        for user_id, question in questions
    ]


def dump_memories() -> None:
    for user_id in [USER_JOHN_DOE, USER_MARY_ANN]:
        for app_id in [APP_FAQ_1, APP_FAQ_2]:
            print(f"\nListing memories for user {user_id} from {app_id}:")
            data = MemoryStore(app_id).list_memories(
                user_id=user_id, kind=MemoryItemKind.CHAT_SUMMARY
            )
            print(json.dumps([m.as_dict() for m in data], indent=2, default=str))
            print("\n")


def main() -> None:
    init_memory_store()

    agent_client_1 = MyAgent(APP_FAQ_1)
    agent_client_2 = MyAgent(APP_FAQ_2)

    # user john_doe sends a series of messages to the agent 1, which are stored in the
    # memory store
    for messages in [MSG_SOCCER, MSG_AZURE]:
        chat_with_agent(agent_client_1, USER_JOHN_DOE, messages)

    # user john_doe sends a series of messages to the agent 2, which are stored in the
    # memory store. agent 1 should not be able to see these memories, and
    # agent 2 should not be able to see the memories from agent 1.
    chat_with_agent(agent_client_2, USER_JOHN_DOE, MSG_COFFEE)

    # user mary_ann sends messages to the agent 1, which are stored in the
    # memory store
    chat_with_agent(agent_client_1, USER_MARY_ANN, MSG_ITALIAN_FOOD)

    sleep_for_memory_extraction()

    # john should only be able to see his own memories
    # and mary should only be able to see her own memories
    responses = ask_agent_about_memories(
        agent=agent_client_1,
        questions=[
            (
                USER_JOHN_DOE,
                "Do you know the team that I am supporting for the World Cup.",
            ),
            (USER_JOHN_DOE, "Do you know if I love to drink coffee?"),
            (
                USER_MARY_ANN,
                "Do you know the team that I am supporting for the World Cup.",
            ),
            (USER_MARY_ANN, "Do you know if I love Italian food or not."),
        ],
    )
    assert responses == [True, False, False, True]

    responses = ask_agent_about_memories(
        agent=agent_client_2,
        questions=[
            (USER_JOHN_DOE, "Do you know if I love to drink coffee?"),
            (USER_MARY_ANN, "Do you know if I love Italian food or not."),
        ],
    )
    assert responses == [True, False]

    # dump_memories()


if __name__ == "__main__":
    main()
