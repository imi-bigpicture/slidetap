#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.


import logging
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from dotenv import load_dotenv


class ConfigParser:
    def __init__(
        self,
        config: dict[str, Any],
        env: Mapping[str, str] | None = None,
    ) -> None:
        """Build a parser over ``config`` (parsed YAML).

        ``env`` is the source for ``get_env`` / ``get_env_or_none`` lookups.
        Defaults to ``os.environ``; tests can pass an explicit mapping to
        avoid touching real process environment.
        """
        self._config = config
        self._env: Mapping[str, str] = env if env is not None else os.environ

    @classmethod
    def create(cls) -> "ConfigParser":
        load_dotenv()
        logger = logging.getLogger(f"{__name__}.{cls.__name__}")

        config_file = os.environ.get("SLIDETAP_CONFIG_FILE")
        if config_file is None:
            raise ValueError("SLIDETAP_CONFIG_FILE must be set.")

        logger.info(f"Loading configuration from {config_file}.")
        with open(config_file) as file:
            config = yaml.safe_load(file)
        return cls(config=config)

    def contains_yaml_key(self, key: str) -> bool:
        return key in self._config

    def get_yaml(self, key: str | Sequence[str]) -> Any:
        if isinstance(key, str):
            try:
                return self._config[key]
            except KeyError as exception:
                raise KeyError(f"Missing key {key} in config file.") from exception
        if len(key) == 0:
            raise KeyError("Key must not be empty.")
        config = self._config
        for index, key_part in enumerate(key):
            try:
                config = config[key_part]
            except KeyError as exception:
                raise KeyError(
                    f"Missing keys {key[:index]} in config file."
                ) from exception
        return config

    def get_yaml_or_default(self, key: str | Sequence[str], default: Any):
        try:
            return self.get_yaml(key)
        except KeyError:
            return default

    def get_yaml_or_env_or_default(
        self,
        yaml_key: str | Sequence[str],
        env_key: str,
        default: Any,
        cast: Callable[[str], Any] = str,
    ) -> Any:
        """Resolve a value with precedence yaml > env > default.

        YAML values come back as their native type (int/float/bool/etc.).
        Env values are strings; ``cast`` converts them to the wanted type
        (e.g. ``int``, ``float``). Useful for fields that have a
        well-known env-var convention upstream (e.g.
        ``PROCRASTINATE_WORKER_CONCURRENCY``).
        """
        try:
            return self.get_yaml(yaml_key)
        except KeyError:
            pass
        env_value = self._env.get(env_key)
        if env_value is not None:
            return cast(env_value)
        return default

    def get_env(self, key: str, default: Any | None = None) -> Any:
        value = self._env.get(key)
        if value is not None:
            return value
        if default is not None:
            return default
        raise KeyError(f"Missing key {key} in environment variables.")

    def get_env_or_none(self, key: str) -> Any:
        return self._env.get(key)

    def get_sub_parser(self, key: str | Sequence[str]) -> "ConfigParser":
        return ConfigParser(config=self.get_yaml(key), env=self._env)


@dataclass(frozen=True)
class DicomizationConfig:
    levels: Sequence[int] | None = None
    include_labels: bool = False
    include_overviews: bool = False
    threads: int = 1

    @classmethod
    def parse(cls, parser: ConfigParser) -> "DicomizationConfig":
        if not parser.contains_yaml_key("dicomization"):
            return cls()
        parser = parser.get_sub_parser("dicomization")
        include_levels = parser.get_yaml("levels")
        if include_levels is not None and include_levels != "all":
            if isinstance(include_levels, str):
                levels = [int(value) for value in include_levels.split(",")]
            elif isinstance(include_levels, int):
                levels = [include_levels]
            else:
                levels = include_levels
        else:
            levels = None
        threads = parser.get_yaml_or_default("threads", 1)
        include_labels = parser.get_yaml_or_default("include_labels", False)
        include_overviews = parser.get_yaml_or_default("include_overviews", False)
        return cls(levels, include_labels, include_overviews, threads)


@dataclass(frozen=True)
class TaskConfig:
    """Configuration for the background task queue."""

    db_uri: str
    """PostgreSQL DSN."""

    blocking: bool = False
    """When True, run tasks synchronously for local development/tests."""

    concurrency: int = 4
    """Number of jobs a worker process runs in parallel.
    """

    stalled_worker_timeout: float = 30.0
    """Seconds after which Procrastinate considers a silent worker dead.
    """

    log_level: Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"] = (
        "INFO"
    )
    """Root log level for the worker process."""

    @classmethod
    def parse(cls, parser: ConfigParser) -> "TaskConfig":
        db_uri = parser.get_env("SLIDETAP_DBURI")
        if parser.contains_yaml_key("task"):
            sub: ConfigParser = parser.get_sub_parser("task")
        else:
            sub = ConfigParser(config={}, env=parser._env)
        return cls(
            db_uri=db_uri,
            blocking=sub.get_yaml_or_default("blocking", False),
            concurrency=sub.get_yaml_or_env_or_default(
                "concurrency", "PROCRASTINATE_WORKER_CONCURRENCY", 4, int
            ),
            stalled_worker_timeout=sub.get_yaml_or_default(
                "stalled_worker_timeout", 30.0
            ),
            log_level=sub.get_yaml_or_default("log_level", "INFO"),
        )


@dataclass(frozen=True)
class ImageCacheConfig:
    cache_size: int = 10

    @classmethod
    def parse(cls, parser: ConfigParser) -> "ImageCacheConfig":
        if not parser.contains_yaml_key("image_cache"):
            return cls()
        parser = parser.get_sub_parser("image_cache")
        cache_size = parser.get_yaml_or_default("cache_size", None)
        if cache_size is None:
            return cls()
        return cls(cache_size)


@dataclass(frozen=True)
class StorageConfig:
    outbox: Path
    download: Path
    processing: Path
    image_path: str = "images"
    metadata_path: str = "metadata"
    thumbnail_path: str = "thumbnails"
    psuedonym_path: str = "pseudonyms"
    # Prefix for a per-dataset bundle folder nested in the project outbox. When
    # set, image and metadata content is placed under
    # ``<project outbox>/<bundle_prefix><alias>``; when None (default) it goes
    # directly in the project outbox with no extra nesting.
    bundle_prefix: str | None = None

    @classmethod
    def parse(cls, parser: ConfigParser) -> "StorageConfig":
        storage_path = Path(parser.get_env("SLIDETAP_STORAGE"))
        outbox = storage_path.joinpath("storage")
        download = storage_path.joinpath("download")
        processing = storage_path.joinpath("processing")
        return cls(outbox, download, processing)


@dataclass(frozen=True)
class DatabaseConfig:
    uri: str
    no_autoflush: bool

    @classmethod
    def parse(cls, parser: ConfigParser) -> "DatabaseConfig":
        database_uri = parser.get_env("SLIDETAP_DBURI")
        no_autoflush = parser.get_yaml_or_default("no_autoflush", False)

        return cls(database_uri, no_autoflush)


@dataclass(frozen=True)
class LoginConfig:
    secret_key: str
    access_token_expiration_seconds: int = 3600
    keep_alive_seconds: int = 900

    @classmethod
    def parse(cls, parser: ConfigParser) -> "LoginConfig":
        secret_key = parser.get_env("SLIDETAP_SECRET_KEY")
        access_token_expiration_seconds = parser.get_yaml_or_default(
            "access_token_expiration", 3600
        )
        keep_alive_seconds = parser.get_yaml_or_default("keep_alive", 900)

        return cls(secret_key, access_token_expiration_seconds, keep_alive_seconds)


@dataclass(frozen=True)
class MapperConfig:
    mapping_file: Path | None

    @classmethod
    def parse(cls, parser: ConfigParser) -> "MapperConfig":
        mapping_file_str = parser.get_env_or_none("SLIDETAP_MAPPING_FILE")
        mapping_file = Path(mapping_file_str) if mapping_file_str is not None else None
        return cls(mapping_file)


@dataclass(frozen=True)
class SlideTapConfig:
    """SlideTap configuration"""

    restore_projects: bool
    web_app_log_level: Literal[
        "CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"
    ]
    cors_origins: str | None
    use_pseudonyms: bool
    logging_config: dict[str, Any] | None = None

    @classmethod
    def parse(cls, parser: ConfigParser) -> "SlideTapConfig":
        """Parse configuration from ConfigParser."""
        restore_projects = parser.get_yaml_or_default("restore_projects", False)
        web_app_log_level = parser.get_yaml_or_default("log_level", "INFO")
        cors_origins = parser.get_env_or_none("SLIDETAP_CORS_ORIGINS")
        use_pseudonyms = parser.get_yaml_or_default("use_psuedonyms", False)
        logging_config = parser.get_yaml_or_default("logging", None)

        # Parse storage paths
        return cls(
            restore_projects=restore_projects,
            web_app_log_level=web_app_log_level,
            cors_origins=cors_origins,
            use_pseudonyms=use_pseudonyms,
            logging_config=logging_config,
        )
