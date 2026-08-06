from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    opensky_bbox: str = ""
    opensky_poll_seconds: int = 90
    database_url: str = "sqlite:///data/flight_tracker.db"
    log_level: str = "INFO"
    log_format: str = "text"
    cors_origins: str = "*"
    opensky_username: str = ""
    opensky_password: str = ""
    aircraft_registry_db: str = "data/aircraft_registry.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
