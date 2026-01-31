from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    azure_openai_endpoint: str = Field(..., env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str = Field(..., env="AZURE_OPENAI_API_KEY")
    database_url: str = Field(..., env="DATABASE_URL")
    redis_url: str = Field(..., env="REDIS_URL")
    service_bus_namespace: str | None = Field(default=None, env="SERVICE_BUS_NAMESPACE")
    service_bus_queue_name: str | None = Field(default=None, env="SERVICE_BUS_QUEUE_NAME")
    service_bus_connection_string: str | None = Field(
        default=None, env="SERVICE_BUS_CONNECTION_STRING"
    )

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
