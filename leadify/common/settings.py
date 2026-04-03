from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./leadify.db"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/gmail/callback"

    # LLM API Keys
    GEMINI_API_KEY: str = "dummy-key"
    ANTHROPIC_API_KEY: str = "dummy-key"
    MISTRAL_API_KEY: str = "dummy-key"
    TAVILY_API_KEY: str = "dummy-key"

    # Security
    ENCRYPTION_KEY: str = "q_I0H1X0_X0X0X0X0X0X0X0X0X0X0X0X0X0X0X0X0X0=" # Valid 32-byte key

    # Agent Scheduler
    AGENT_CYCLE_MINUTES: int = 60

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"

    # Testing limits (to avoid unintended spam)
    TEST_MODE_EMAIL: bool = True

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
