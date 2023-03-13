import typing
from dataclasses import dataclass

import yaml  # type: ignore

if typing.TYPE_CHECKING:
    from app.web.app import Application


@dataclass
class SessionConfig:
    key: str


@dataclass
class AdminConfig:
    email: str
    password: str


@dataclass
class BotConfig:
    token: str


@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: str = "postgres"
    database: str = "project"


@dataclass
class Config:
    admin: AdminConfig
    session: SessionConfig | None = None
    bot: BotConfig | None = None
    database: DatabaseConfig | None = None


def setup_config(app: "Application", config_path: str) -> None:
    with open(config_path, "r") as f:
        raw_config = yaml.safe_load(f)

    app.config = Config(  # type: ignore
        session=SessionConfig(
            key=raw_config["session"]["key"],
        ),
        admin=AdminConfig(
            email=raw_config["admin"]["email"],
            password=raw_config["admin"]["password"],
        ),
        bot=BotConfig(
            token=raw_config["bot"]["token"],
        ),
        database=DatabaseConfig(**raw_config["database"]),
    )
