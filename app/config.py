from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    app_env: str = "development"
    api_port: int = 8001

    class Config:
        env_file = ".env"

settings = Settings()