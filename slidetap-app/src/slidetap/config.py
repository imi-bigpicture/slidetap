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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Sequence, Union

import yaml
from dotenv import load_dotenv


class ConfigParser:
    def __init__(
        self,
        config: Dict[str, Any],
    ) -> None:
        self._config = config

    @classmethod
    def create(cls) -> "ConfigParser":
        load_dotenv()
        logger = logging.getLogger(f"{__name__}.{cls.__class__.__name__}")

        config_file = os.environ.get("SLIDETAP_CONFIG_FILE")
        if config_file is None:
            raise ValueError("SLIDETAP_CONFIG_FILE must be set.")

        logger.info(f"Loading configuration from {config_file}.")
        with open(config_file, "r") as file:
            config = yaml.safe_load(file)
        return cls(config=config)

    def contains_yaml_key(self, key: str) -> bool:
        return key in self._config

    def get_yaml(self, key: Union[str, Sequence[str]]) -> Any:
        if isinstance(key, str):
            try:
                return self._config[key]
            except KeyError as exception:
                raise KeyError(f"Missing key {key} in config file.", exception)
        if len(key) == 0:
            raise KeyError("Key must not be empty.")
        config = self._config
        for index, key_part in enumerate(key):
            try:
                config = config[key_part]
            except KeyError as exception:
                raise KeyError(f"Missing keys {key[:index]} in config file.", exception)
        return config

    def get_yaml_or_default(self, key: Union[str, Sequence[str]], default: Any):
        try:
            return self.get_yaml(key)
        except KeyError:
            return default

    def get_env(self, key: str, default: Optional[Any] = None) -> Any:
        value = os.environ.get(key)
        if value is not None:
            return value
        if default is not None:
            return default
        raise KeyError(f"Missing key {key} in environment variables.")

    def get_env_or_none(self, key: str) -> Any:
        return os.environ.get(key)

    def get_sub_parser(self, key: Union[str, Sequence[str]]) -> "ConfigParser":
        return ConfigParser(config=self.get_yaml(key))


@dataclass(frozen=True)
class DicomizationConfig:
    levels: Optional[Sequence[int]] = None
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
class CeleryConfig:
    broker_url: Optional[str] = None
    worker_concurrency: Optional[int] = None
    worker_max_tasks_per_child: Optional[int] = None
    worker_max_memory_per_child: Optional[int] = None
    blocking: bool = False

    @classmethod
    def parse(cls, parser: ConfigParser) -> "CeleryConfig":
        broker_url = parser.get_env("SLIDETAP_BROKER_URL")
        if not parser.contains_yaml_key("celery"):
            return cls(broker_url)
        parser = parser.get_sub_parser("celery")
        concurrency = parser.get_yaml_or_default("concurrency", None)
        max_tasks_per_child = parser.get_yaml_or_default("max_tasks_per_child", None)
        max_memory_per_child = parser.get_yaml_or_default("max_memory_per_child", None)
        blocking = parser.get_yaml_or_default("blocking", False)
        return cls(
            broker_url, concurrency, max_tasks_per_child, max_memory_per_child, blocking
        )

    @property
    def dict_config(self) -> Dict[str, Any]:
        """Return configuration for Celery."""
        return {
            "broker_url": self.broker_url,
            "worker_concurrency": self.worker_concurrency,
            "worker_max_tasks_per_child": self.worker_max_tasks_per_child,
            "worker_max_memory_per_child": self.worker_max_memory_per_child,
            "task_ignore_result": True,
            "broker_connection_retry_on_startup": True,
            "task_always_eager": self.blocking,
            "task_eager_propagates": self.blocking,
            # "hijack_root_logger": False,
        }


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
    image_path: str = "images"
    metadata_path: str = "metadata"
    thumbnail_path: str = "thumbnails"
    psuedonym_path: str = "pseudonyms"

    @classmethod
    def parse(cls, parser: ConfigParser) -> "StorageConfig":
        storage_path = Path(parser.get_env("SLIDETAP_STORAGE"))
        outbox = storage_path.joinpath("storage")
        download = storage_path.joinpath("download")
        return cls(outbox, download)


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
    mapping_file: Optional[Path]

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
    cors_origins: Optional[str]
    use_pseudonyms: bool

    @classmethod
    def parse(cls, parser: ConfigParser) -> "SlideTapConfig":
        """Parse configuration from ConfigParser."""
        restore_projects = parser.get_yaml_or_default("restore_projects", False)
        web_app_log_level = parser.get_yaml_or_default("log_level", "INFO")
        cors_origins = parser.get_env_or_none("SLIDETAP_CORS_ORIGINS")
        use_pseudonyms = parser.get_yaml_or_default("use_psuedonyms", False)

        # Parse storage paths
        return cls(
            restore_projects=restore_projects,
            web_app_log_level=web_app_log_level,
            cors_origins=cors_origins,
            use_pseudonyms=use_pseudonyms,
        )
