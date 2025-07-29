import os
from typing import Optional

from pydantic import validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SERVICE_NAME: str = "AIMate"

    GEMINI_API_KEY: str = None

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str =  "text" #"json"
    TRACE_CALLER: bool = True

    #sqlite
    DATABASE_FILE_NAME: str = "database.db"


    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    SQLALCHEMY_DATABASE_URI: Optional[str] = None
    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: str | None, values: dict[str, any]) -> any:
        if isinstance(v, str):
            return v
        db_path = os.path.join(os.path.abspath("."), "core", "cache", "sqlite_db", values.get("DATABASE_FILE_NAME"))
        url = f"sqlite+pysqlite:///{db_path}"
        return url

settings = Settings() 