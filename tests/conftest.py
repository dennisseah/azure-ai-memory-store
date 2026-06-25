import pytest
from pydantic_settings import SettingsConfigDict

from azure_ai_memory_store import myagent
from azure_ai_memory_store.services import memory_store


@pytest.fixture(autouse=True)
def _test_env(monkeypatch):
    """Provide deterministic settings and never read the developer's local .env."""
    env_vars = {
        "FOUNDRY_PROJECT_ENDPOINT": "https://example.test",
        "MEMORY_STORE_CHAT_MODEL_DEPLOYMENT_NAME": "chat-model",
        "MEMORY_STORE_EMBEDDING_MODEL_DEPLOYMENT_NAME": "embed-model",
        "TENANT_ID": "tenant-a",
        "APP_ID": "app-a",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    no_env_file = SettingsConfigDict(env_file=None, extra="ignore")
    monkeypatch.setattr(myagent.MyAgentEnv, "model_config", no_env_file)
    monkeypatch.setattr(memory_store.MemoryStoreEnv, "model_config", no_env_file)
