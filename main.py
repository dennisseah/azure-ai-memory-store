import time

from azure_ai_memory_store.myagent import MyAgent
from azure_ai_memory_store.services.memory_store import MemoryStore

user_id = "john_doe"


def main():
    # Ensure the memory store exists before the agent references it.
    MemoryStore().clear_memory(user_id=user_id)
    # Deletes are eventually consistent: the memory search index lags behind
    # delete_memory, so pause to let it catch up before the next chat.
    time.sleep(5)

    agent_client = MyAgent()
    # message = "I am rooting for England to win the World Cup."

    # print("Sending message to agent:", message)
    # response, _ = agent_client.chat(user_id=user_id, message=message)
    # print("Response:", response.output_text)

    # # The MemorySearchPreviewTool extracts memories from the conversation
    # # automatically after `update_delay` seconds of inactivity. Wait for that
    # # asynchronous extraction to complete before starting a new conversation.
    # print("\nWaiting for memories to be stored...\n")
    # time.sleep(65)

    message = "Do you know the team that I am supporting for the World Cup."
    print("Sending message to agent:", message)
    response, _ = agent_client.chat(user_id=user_id, message=message)
    print("Response:", response.output_text)


if __name__ == "__main__":
    main()
