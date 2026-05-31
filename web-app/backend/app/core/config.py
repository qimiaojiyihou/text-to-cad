"""应用配置管理"""

from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""
    LLM_MODEL: str = "gpt-4o"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_HASH_ROUNDS: int = 12

    # Paths
    # config.py -> core/ -> app/ -> backend/ -> web-app/ -> repo_root
    REPO_ROOT: Path = Path(__file__).resolve().parents[4]
    GENERATED_DIR: Path = REPO_ROOT / "web-app" / "generated_models"
    DATABASE_URL: str = f"sqlite:///{REPO_ROOT / 'web-app' / 'app.db'}"

    class Config:
        env_file = Path(__file__).resolve().parent.parent.parent / ".env"
        env_file_encoding = "utf-8"


_settings = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
