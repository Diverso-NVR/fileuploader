import logging
import typing

from pydantic import BaseSettings, Field


def create_logger(mode="INFO"):
    logs = {"INFO": logging.INFO, "DEBUG": logging.DEBUG}

    logger = logging.getLogger("fileuploader")
    logger.setLevel(logs[mode])

    handler = logging.StreamHandler()
    handler.setLevel(logs[mode])

    formatter = logging.Formatter(
        "%(levelname)-8s  %(asctime)s    %(message)s", datefmt="%d-%m-%Y %I:%M:%S %p"
    )

    handler.setFormatter(formatter)

    logger.addHandler(handler)


class Settings(BaseSettings):
    google_creds_path: str = Field(..., env="GOOGLE_CREDS_PATH")
    google_drive_token_path: str = Field(..., env="GOOGLE_DRIVE_TOKEN_PATH")
    google_calendar_token_path: str = Field(..., env="GOOGLE_CALENDAR_TOKEN_PATH")

    google_calendar_scopes: typing.Set[str] = Field(..., env="GOOGLE_CALENDAR_SCOPES")
    google_drive_scopes: typing.Set[str] = Field(..., env="GOOGLE_DRIVE_SCOPES")

    psql_url: str = Field(..., env="PSQL_URL")
    redis_url: str = Field(..., env="REDIS_URL")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings(_env_file="../.env")
