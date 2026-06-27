import pytest

from azure_ai_memory_store import myagent as myagent_module
from azure_ai_memory_store.myagent import MyAgent


@pytest.fixture
def mock_project_client(mocker):
    client = mocker.MagicMock()
    mocker.patch.object(myagent_module, "AIProjectClient", return_value=client)
    mocker.patch.object(
        myagent_module, "DefaultAzureCredential", return_value=mocker.MagicMock()
    )
    return client


@pytest.fixture
def agent(mock_project_client):
    return MyAgent("app-a")


def test_init_builds_client_with_endpoint(mocker):
    ctor = mocker.patch.object(myagent_module, "AIProjectClient")
    mocker.patch.object(myagent_module, "DefaultAzureCredential")

    MyAgent("app-a")

    assert ctor.call_args.kwargs["endpoint"] == "https://example.test"


def test_memory_store_name(agent):
    assert agent.memory_store_name == "app-a-memory-store"


def test_chat_creates_conversation_when_none(agent, mock_project_client):
    openai_client = mock_project_client.get_openai_client.return_value
    openai_client.conversations.create.return_value.id = "conv-1"
    response_obj = openai_client.responses.create.return_value

    response, conversation_id = agent.chat("john_doe", "hello")

    assert response is response_obj
    assert conversation_id == "conv-1"
    openai_client.conversations.create.assert_called_once_with()
    openai_client.responses.create.assert_called_once()
    kwargs = openai_client.responses.create.call_args.kwargs
    assert kwargs["model"] == "chat-model"
    assert kwargs["input"] == "hello"
    assert kwargs["conversation"] == "conv-1"
    tool = kwargs["tools"][0]
    assert tool.memory_store_name == "app-a-memory-store"
    assert tool.scope == "john_doe"


def test_chat_reuses_existing_conversation_id(agent, mock_project_client):
    openai_client = mock_project_client.get_openai_client.return_value

    _, conversation_id = agent.chat("john_doe", "hi", conversation_id="conv-existing")

    assert conversation_id == "conv-existing"
    openai_client.conversations.create.assert_not_called()
    openai_client.responses.create.assert_called_once()
    kwargs = openai_client.responses.create.call_args.kwargs
    assert kwargs["input"] == "hi"
    assert kwargs["conversation"] == "conv-existing"
    tool = kwargs["tools"][0]
    assert tool.scope == "john_doe"


def test_close_conversation_deletes(agent, mock_project_client):
    openai_client = mock_project_client.get_openai_client.return_value

    agent.close_conversation("conv-1")

    openai_client.conversations.delete.assert_called_once_with("conv-1")


def test_close_conversation_noop_when_none(agent, mock_project_client):
    agent.close_conversation(None)

    mock_project_client.get_openai_client.assert_not_called()
