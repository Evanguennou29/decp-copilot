from decp.config import load_settings


def test_load_settings_defaults_to_no_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = load_settings()
    assert settings.has_llm_key is False


def test_load_settings_detects_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    settings = load_settings()
    assert settings.has_llm_key is True


def test_load_settings_reads_data_dir(monkeypatch):
    monkeypatch.setenv("DECP_DATA_DIR", "/tmp/decp-data")
    settings = load_settings()
    assert settings.data_dir == "/tmp/decp-data"
