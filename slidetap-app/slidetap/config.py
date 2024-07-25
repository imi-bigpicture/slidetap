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
from os import environ
from pathlib import Path
from typing import Any, Dict, Literal, Optional, Sequence, Union

import yaml
from dotenv import load_dotenv


@dataclass
class DicomizationConfig:
    levels: Optional[Sequence[int]] = None
    include_labels: bool = False
    include_overviews: bool = False
    threads: int = 1

    @classmethod
    def from_config(cls, config: Optional[Dict[str, Any]]) -> "DicomizationConfig":
        if config is None:
            return cls()
        include_levels: Optional[Union[str, int, Sequence[int]]] = config.get(
            "levels", None
        )
        if include_levels is not None and include_levels != "all":
            if isinstance(include_levels, str):
                levels = [int(value) for value in include_levels.split(",")]
            elif isinstance(include_levels, int):
                levels = [include_levels]
            else:
                levels = include_levels
        else:
            levels = None
        threads = int(config.get("threads", 1))
        include_labels = bool(config.get("include_labels", False))
        include_overviews = bool(config.get("include_overviews", False))

        return cls(levels, include_labels, include_overviews, threads)


@dataclass
class SchedulerConfig:
    default_queue_workers: int = 1
    high_queue_workers: int = 1

    @classmethod
    def from_config(cls, config: Optional[Dict[str, Any]]) -> "SchedulerConfig":
        if config is None:
            return cls()
        default_queue_workers = int(config.get("default_queue_workers", 1))
        high_queue_workers = int(config.get("high_queue_workers", 1))
        return cls(default_queue_workers, high_queue_workers)


@dataclass
class CeleryConfig:
    broker_url: Optional[str] = None

    @classmethod
    def from_config(cls, config: Optional[Dict[str, Any]]) -> "CeleryConfig":
        if config is None:
            return cls()
        broker_url = config.get("broker_url", None)
        return cls(broker_url)


class Config:
    """Base configuration"""

    def __init__(self):
        self._flask_testing = False
        self._flask_debug = False
        load_dotenv()
        config_file = environ.get("SLIDETAP_CONFIG_FILE")
        if config_file is None:
            raise ValueError("SLIDETAP_CONFIG_FILE must be set.")
        try:
            with open(config_file, "r") as file:
                config: Dict[str, Any] = yaml.safe_load(file)
                self._parse_yaml_config(config)
            self._parse_env_config()
        except KeyError as e:
            raise ValueError(f"Missing key {e} in config file {config_file}.")

    def _parse_yaml_config(self, config: Dict[str, Any]) -> None:
        self._keepalive = int(config["keepalive"])
        self._enforce_https = config.get("enforce_https", True)
        self._dicomization_config = DicomizationConfig.from_config(
            config.get("dicomization", None)
        )
        self._scheduler_config = SchedulerConfig.from_config(
            config.get("scheduler", None)
        )
        self._restore_projects = bool(config.get("restore_projects", False))
        self._log_level = config.get("log_level", "INFO")
        self._secret_key = str(config.get("secret_key"))
        self._use_psuedonyms = bool(config.get("use_psuedonyms", False))

    def _parse_env_config(self):
        self._database = environ["SLIDETAP_DBURI"]
        self._storage_path = Path(environ["SLIDETAP_STORAGE"])
        self._webapp_url = environ["SLIDETAP_WEBAPP_URL"]
        broker_url = environ.get("SLIDETAP_BROKER_URL")
        self._celery_config = CeleryConfig(broker_url=broker_url)

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
            "task_ignore_result": True,
            "broker_connection_retry_on_startup": True,
        }

    @property
    def dicomization_config(self) -> DicomizationConfig:
        """Return configuration for dicomization."""
        return self._dicomization_config

    @property
    def scheduler_config(self) -> SchedulerConfig:
        """Return configuration for scheduler."""
        return self._scheduler_config

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
        self._scheduler_config = SchedulerConfig()
        self._celery_config = CeleryConfig(broker_url="memory://")
        self._secret_key = "test"
        self._use_psuedonyms = True
