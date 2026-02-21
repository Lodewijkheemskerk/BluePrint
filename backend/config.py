from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Exchange
    exchange_id: str = "binance"

    # Universe
    dynamic_universe_size: int = 100

    # Scanning
    scan_interval_minutes: int = 240

    # Telegram (optional)
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None

    # Database
    database_url: str = "sqlite:///./blueprint.db"

    # Server
    host: str = "127.0.0.1"
    port: int = 8000

    # Quote currency for pairs
    quote_currency: str = "USDT"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
