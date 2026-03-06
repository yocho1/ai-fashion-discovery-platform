from core.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.app_name == "AI Fashion Discovery API"
    assert settings.app_env in {"dev", "test", "prod"}
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.redis_url.startswith("redis://")
