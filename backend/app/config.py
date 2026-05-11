from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/

class Settings(BaseSettings):
    DB_TYPE: str  # "postgres" or "sqlite"

    LOG_LEVEL: str = "INFO"
    
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int | None = None
    POSTGRES_DB: str | None = None

    SQLITE_DB_PATH: str = "./app.db"

    SECRET_KEY: str
    ALGORITHM: str
    EXPIRATION_TIME: int
    ADMIN_TOKEN: str
    
    MAX_UPLOAD_SIZE_MB: int = 10
    MAX_UPLOAD_UNCOMPRESSED_MB: int = 50
    
    MAX_PROJECTS_PER_USER: int = 20
    
    CORS_ORIGINS: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env"
    )

    @computed_field
    def DATABASE_URL(self) -> str:
        if self.DB_TYPE == "sqlite":
            return f"sqlite:///{self.SQLITE_DB_PATH}"

        return (
            f"postgresql+psycopg2://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
            f"/{self.POSTGRES_DB}"
        )


settings = Settings()