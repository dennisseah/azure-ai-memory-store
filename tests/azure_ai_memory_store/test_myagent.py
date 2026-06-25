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
    return MyAgent()


def test_init_builds_client_with_endpoint(mocker):
    ctor = mocker.patch.object(myagent_module, "AIProjectClient")
    mocker.patch.object(myagent_module, "DefaultAzureCredential")

    MyAgent()

    assert ctor.call_args.kwargs["endpoint"] == "https://example.test"


def test_scope_composes_tenant_app_user(agent):
    assert agent._scope("john_doe") == "tenant-a_app-a_john_doe"


def test_memory_store_name(agent):
    assert agent._memory_store_name() == "tenant-a-app-a-memory-store"


def test_remember_updates_memories_immediately(agent, mock_project_client):
    poller = mock_project_client.beta.memory_stores.begin_update_memories.return_value

    agent.remember("john_doe", "I like tea")

    mock_project_client.beta.memory_stores.begin_update_memories.assert_called_once_with(
        name="tenant-a-app-a-memory-store",
        scope="tenant-a_app-a_john_doe",
        items="I like tea",
        update_delay=0,
    )
    poller.result.assert_called_once_with()


def test_create_agent_builds_version_with_memory_tool(agent, mock_project_client):
    created = mock_project_client.agents.create_version.return_value

    result = agent._create_agent("john_doe")

    assert result is created
    mock_project_client.agents.create_version.assert_called_once()
    kwargs = mock_project_client.agents.create_version.call_args.kwargs
    assert kwargs["agent_name"] == "MyAgent"

    definition = kwargs["definition"]
    assert definition.model == "chat-model"
    assert len(definition.tools) == 1

    tool = definition.tools[0]
    assert tool.memory_store_name == "tenant-a-app-a-memory-store"
    assert tool.scope == "tenant-a_app-a_john_doe"


def test_chat_creates_conversation_when_none(agent, mock_project_client):
    openai_client = mock_project_client.get_openai_client.return_value
    openai_client.conversations.create.return_value.id = "conv-1"
    response_obj = openai_client.responses.create.return_value
    mock_project_client.agents.create_version.return_value.name = "MyAgent"

    response, conversation_id = agent.chat("john_doe", "hello")

    assert response is response_obj
    assert conversation_id == "conv-1"
    openai_client.conversations.create.assert_called_once_with()
    openai_client.responses.create.assert_called_once_with(
        input="hello",
        conversation="conv-1",
        extra_body={"agent_reference": {"name": "MyAgent", "type": "agent_reference"}},
    )


def test_chat_reuses_existing_conversation_id(agent, mock_project_client):
    openai_client = mock_project_client.get_openai_client.return_value
    mock_project_client.agents.create_version.return_value.name = "MyAgent"

    _, conversation_id = agent.chat("john_doe", "hi", conversation_id="conv-existing")

    assert conversation_id == "conv-existing"
    openai_client.conversations.create.assert_not_called()
    openai_client.responses.create.assert_called_once_with(
        input="hi",
        conversation="conv-existing",
        extra_body={"agent_reference": {"name": "MyAgent", "type": "agent_reference"}},
    )


def test_close_conversation_deletes(agent, mock_project_client):
    openai_client = mock_project_client.get_openai_client.return_value

    agent.close_conversation("conv-1")

    openai_client.conversations.delete.assert_called_once_with("conv-1")


def test_close_conversation_noop_when_none(agent, mock_project_client):
    agent.close_conversation(None)

    mock_project_client.get_openai_client.assert_not_called()
