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

"""Flask configuration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Sequence, Union

import yaml
from dotenv import dotenv_values


class ConfigParser:
    def __init__(self, env: Dict[str, Any], config: Dict[str, Any]) -> None:
        self._env = env
        self._config = config

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
        try:
            return self._env.get(key)
        except KeyError as exception:
            if default is not None:
                return default
            raise KeyError(f"Missing key {key} in environment variables.", exception)

    def get_sub_parser(self, key: Union[str, Sequence[str]]) -> "ConfigParser":
        return ConfigParser(self._env, self.get_yaml(key))


@dataclass
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


@dataclass
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

        return cls(broker_url, concurrency, max_tasks_per_child, max_memory_per_child)


class Config:
    """Base configuration"""

    def __init__(self, env: Optional[Dict[str, Any]] = None):
        self._flask_testing = False
        self._flask_debug = False
        if env is None:
            env = dotenv_values()
        config_file = env.get("SLIDETAP_CONFIG_FILE")
        if config_file is None:
            raise ValueError("SLIDETAP_CONFIG_FILE must be set.")
        with open(config_file, "r") as file:
            config: Dict[str, Any] = yaml.safe_load(file)
            parser = ConfigParser(env, config)
            self._parse(parser)

    def _parse(self, parser: ConfigParser):
        self._keepalive = parser.get_yaml("keepalive")
        self._enforce_https = parser.get_yaml_or_default("enforce_https", True)
        self._dicomization_config = DicomizationConfig.parse(parser)
        self._celery_config = CeleryConfig.parse(parser)
        self._restore_projects = parser.get_yaml_or_default("restore_projects", False)
        self._log_level = parser.get_yaml_or_default("log_level", "INFO")
        self._secret_key = parser.get_env("SLIDETAP_SECRET_KEY")
        self._use_psuedonyms = parser.get_yaml_or_default("use_psuedonyms", False)
        self._database = parser.get_env("SLIDETAP_DBURI")
        self._storage_path = Path(parser.get_env("SLIDETAP_STORAGE"))
        self._webapp_url = parser.get_env("SLIDETAP_WEBAPP_URL")

    @property
    def storage_path(self) -> Path:
        """Return the storage path."""
        return Path(self._storage_path)

    @property
    def keepalive(self) -> int:
        """Return the keepalive time."""
        return int(self._keepalive)

    @property
    def enforce_https(self):
        """Return whether to enforce https."""
        return self._enforce_https

    @property
    def webapp_url(self):
        """Return the webapp URL."""
        return self._webapp_url

    @property
    def flask_log_level(
        self,
    ) -> Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]:
        """Return the log level for Flask."""
        return self._log_level

    @property
    def restore_projects(self) -> bool:
        """Return whether to restore projects."""
        return self._restore_projects

    @property
    def flask_config(self) -> Dict[str, Any]:
        """Return configuration for Flask."""
        return {
            "DEBUG": self._flask_debug,
            "TESTING": self._flask_testing,
            "SQLALCHEMY_DATABASE_URI": self._database,
            "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            "SQLALCHEMY_ENGINE_OPTIONS": {"pool_pre_ping": True},
            "SECRET_KEY": self._secret_key,
        }

    @property
    def celery_config(self) -> Dict[str, Any]:
        """Return configuration for Celery."""
        return {
            "broker_url": self._celery_config.broker_url,
            "worker_concurrency": self._celery_config.worker_concurrency,
            "worker_max_tasks_per_child": self._celery_config.worker_max_tasks_per_child,
            "worker_max_memory_per_child": self._celery_config.worker_max_memory_per_child,
            "task_ignore_result": True,
            "broker_connection_retry_on_startup": True,
            "task_always_eager": self._celery_config.blocking,
            "task_eaker_propagates": self._celery_config.blocking,
            # "hijack_root_logger": False,
        }

    @property
    def dicomization_config(self) -> DicomizationConfig:
        """Return configuration for dicomization."""
        return self._dicomization_config

    @property
    def use_pseudonyms(self) -> bool:
        """Return whether to use pseudonyms."""
        return self._use_psuedonyms


class ConfigProduction(Config):
    pass


class ConfigDevelopment(Config):
    """Enables debug mode, reload on change."""

    DEBUG = True
    TESTING = True


class ConfigTest(Config):
    """Testing configuration."""

    def __init__(self, storage_path: Path, tempdir: Path):
        self._flask_testing = True
        self._flask_debug = True
        self._storage_path = storage_path
        self._keepalive = 30
        self._database = f"sqlite:///{tempdir}/test.db"
        self._webapp_url = "http://localhost:13000"
        self._enforce_https = False
        self._log_level = "INFO"
        self._restore_projects = False
        self._dicomization_config = DicomizationConfig()
        self._celery_config = CeleryConfig(blocking=True)
        self._secret_key = "test"
        self._use_psuedonyms = True
