import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Enterprise LangGraph Agent"
    DEBUG: bool = True
    
    # Redis Settings
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # LLM Settings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # KB Model Settings
    KB_LLM_MODEL: str = os.getenv("KB_LLM_MODEL", "gpt-3.5-turbo")
    KB_LLM_BASE_URL: Optional[str] = os.getenv("KB_LLM_BASE_URL", None)
    KB_LLM_API_KEY: Optional[str] = os.getenv("KB_LLM_API_KEY", None)

    # Action Model Settings
    ACTION_LLM_MODEL: str = os.getenv("ACTION_LLM_MODEL", "gpt-4-turbo")
    ACTION_LLM_BASE_URL: Optional[str] = os.getenv("ACTION_LLM_BASE_URL", None)
    ACTION_LLM_API_KEY: Optional[str] = os.getenv("ACTION_LLM_API_KEY", None)

    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev_secret_key_change_me")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    
    # Middleware Settings
    PII_REDACTION_ENABLED: bool = True
    RAI_CHECK_ENABLED: bool = True

    model_config = {
        "env_file": ".env"
    }

settings = Settings()
