import pytest
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

from azure_ai_memory_store.services import memory_store as memory_store_module
from azure_ai_memory_store.services.memory_store import MemoryStore


@pytest.fixture
def mock_project_client(mocker):
    client = mocker.MagicMock()
    mocker.patch.object(memory_store_module, "AIProjectClient", return_value=client)
    mocker.patch.object(
        memory_store_module,
        "DefaultAzureCredential",
        return_value=mocker.MagicMock(),
    )
    return client


def test_init_uses_existing_store(mock_project_client):
    store = MemoryStore()

    assert store.name == "tenant-a-app-a-memory-store"
    assert store.scope_prefix == "tenant-a_app-a"
    mock_project_client.beta.memory_stores.get.assert_called_once_with(
        name="tenant-a-app-a-memory-store"
    )
    mock_project_client.beta.memory_stores.create.assert_not_called()


def test_init_creates_store_when_missing(mock_project_client):
    mock_project_client.beta.memory_stores.get.side_effect = ResourceNotFoundError(
        "missing"
    )

    MemoryStore()

    mock_project_client.beta.memory_stores.create.assert_called_once()
    kwargs = mock_project_client.beta.memory_stores.create.call_args.kwargs
    assert kwargs["name"] == "tenant-a-app-a-memory-store"
    assert kwargs["description"] == "Memory store with 30-day default TTL"


def test_clear_memory_deletes_each_memory(mock_project_client, mocker):
    m1 = mocker.MagicMock(memory_id="m1")
    m2 = mocker.MagicMock(memory_id="m2")
    # First pass returns memories, second pass is empty so the loop stops.
    mock_project_client.beta.memory_stores.list_memories.side_effect = [
        [m1, m2],
        [],
    ]
    sleep = mocker.patch.object(memory_store_module.time, "sleep")

    store = MemoryStore()
    store.clear_memory("john_doe")

    mock_project_client.beta.memory_stores.list_memories.assert_any_call(
        name="tenant-a-app-a-memory-store", scope="tenant-a_app-a_john_doe", kind=None
    )
    assert mock_project_client.beta.memory_stores.delete_memory.call_count == 2
    mock_project_client.beta.memory_stores.delete_memory.assert_any_call(
        name="tenant-a-app-a-memory-store", memory_id="m1"
    )
    mock_project_client.beta.memory_stores.delete_memory.assert_any_call(
        name="tenant-a-app-a-memory-store", memory_id="m2"
    )
    sleep.assert_called_once_with(5.0)


def test_clear_memory_stops_after_passes_when_not_empty(mock_project_client, mocker):
    m1 = mocker.MagicMock(memory_id="m1")
    mock_project_client.beta.memory_stores.list_memories.return_value = [m1]
    sleep = mocker.patch.object(memory_store_module.time, "sleep")

    store = MemoryStore()
    store.clear_memory("john_doe", passes=2)

    assert mock_project_client.beta.memory_stores.list_memories.call_count == 2
    assert mock_project_client.beta.memory_stores.delete_memory.call_count == 2
    sleep.assert_called_once_with(5.0)


def test_list_memories_returns_memories_for_user(mock_project_client, mocker):
    m1 = mocker.MagicMock(memory_id="m1")
    m2 = mocker.MagicMock(memory_id="m2")
    mock_project_client.beta.memory_stores.list_memories.return_value = [m1, m2]

    store = MemoryStore()
    memories = store.list_memories("john_doe")

    assert memories == [m1, m2]
    mock_project_client.beta.memory_stores.list_memories.assert_called_once_with(
        name="tenant-a-app-a-memory-store", scope="tenant-a_app-a_john_doe", kind=None
    )


def test_list_memories_retries_then_succeeds(mock_project_client, mocker):
    sleep = mocker.patch.object(memory_store_module.time, "sleep")
    m1 = mocker.MagicMock(memory_id="m1")
    mock_project_client.beta.memory_stores.list_memories.side_effect = [
        HttpResponseError("boom"),
        [m1],
    ]

    store = MemoryStore()
    result = store.list_memories("john_doe")

    assert result == [m1]
    assert mock_project_client.beta.memory_stores.list_memories.call_count == 2
    sleep.assert_called_once_with(2)


def test_list_memories_raises_after_exhausting_retries(mock_project_client, mocker):
    mocker.patch.object(memory_store_module.time, "sleep")
    mock_project_client.beta.memory_stores.list_memories.side_effect = (
        HttpResponseError("boom")
    )

    store = MemoryStore()
    with pytest.raises(HttpResponseError):
        store.list_memories("john_doe")

    assert mock_project_client.beta.memory_stores.list_memories.call_count == 3
