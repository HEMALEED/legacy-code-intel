from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://lcip:lcip@localhost:5432/lcip"
    redis_url: str = "redis://localhost:6379/0"

    storage_backend: str = "local"          # "local" | "s3"
    storage_local_root: str = "./uploads"
    s3_bucket: str = ""
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    llm_provider: str = "openai"            # "openai" | "watsonx"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    watsonx_api_key: str = ""
    watsonx_project_id: str = ""
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    watsonx_model: str = "ibm/granite-13b-chat-v2"

    secret_key: str = "change-me"
    max_upload_bytes: int = 52_428_800      # 50 MB


settings = Settings()
