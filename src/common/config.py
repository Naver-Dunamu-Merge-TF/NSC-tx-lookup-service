from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping


ALLOWED_ENVS = {"local", "dev", "prod"}


@dataclass(frozen=True)
class AppConfig:
    app_env: str
    log_level: str
    database_url: str
    kafka_brokers: str
    service_name: str


def _get_env(env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key, default)
    return value.strip() if isinstance(value, str) else default


def load_config(env: Mapping[str, str] | None = None) -> AppConfig:
    source = env or os.environ
    app_env = _get_env(source, "APP_ENV", "local")
    if app_env not in ALLOWED_ENVS:
        raise ValueError(
            f"APP_ENV must be one of {sorted(ALLOWED_ENVS)} (got {app_env!r})"
        )

    return AppConfig(
        app_env=app_env,
        log_level=_get_env(source, "LOG_LEVEL", "INFO"),
        database_url=_get_env(
            source, "DATABASE_URL", "postgresql://bo:bo@localhost:5432/bo"
        ),
        kafka_brokers=_get_env(source, "KAFKA_BROKERS", "localhost:9092"),
        service_name=_get_env(source, "SERVICE_NAME", "tx-lookup-service"),
    )
