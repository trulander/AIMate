from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    SERVICE_NAME: str = "AIMate"

    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str =  "text" #"json"
    TRACE_CALLER: bool = True

    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

settings = Settings() 