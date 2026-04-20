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

from typing import Any, Dict

import pytest
from slidetap.config import CeleryConfig, ConfigParser


@pytest.fixture()
def broker_url() -> str:
    return "amqp://localhost"


@pytest.fixture()
def empty_config(broker_url: str) -> ConfigParser:
    parser = ConfigParser(config={})
    parser.get_env = lambda key, default=None: broker_url if key == "SLIDETAP_BROKER_URL" else default  # type: ignore[method-assign]
    return parser


@pytest.fixture()
def config_with_celery(broker_url: str) -> ConfigParser:
    def _make(celery_config: Dict[str, Any]) -> ConfigParser:
        parser = ConfigParser(config={"celery": celery_config})
        parser.get_env = lambda key, default=None: broker_url if key == "SLIDETAP_BROKER_URL" else default  # type: ignore[method-assign]
        return parser
    return _make  # type: ignore[return-value]


@pytest.mark.unittest
class TestCeleryConfig:
    def test_default_heartbeat_when_no_celery_section(self, empty_config: ConfigParser):
        # Arrange

        # Act
        config = CeleryConfig.parse(empty_config)

        # Assert
        assert config.broker_heartbeat == 120

    def test_default_heartbeat_when_celery_section_omits_key(self, config_with_celery):
        # Arrange
        parser = config_with_celery({"concurrency": 2})

        # Act
        config = CeleryConfig.parse(parser)

        # Assert
        assert config.broker_heartbeat == 120

    def test_custom_heartbeat_value(self, config_with_celery):
        # Arrange
        parser = config_with_celery({"broker_heartbeat": 60})

        # Act
        config = CeleryConfig.parse(parser)

        # Assert
        assert config.broker_heartbeat == 60

    def test_heartbeat_zero_disables_heartbeat(self, config_with_celery):
        # Arrange
        parser = config_with_celery({"broker_heartbeat": 0})

        # Act
        config = CeleryConfig.parse(parser)

        # Assert
        assert config.broker_heartbeat == 0

    def test_heartbeat_propagates_to_dict_config(self, config_with_celery):
        # Arrange
        parser = config_with_celery({"broker_heartbeat": 30})

        # Act
        config = CeleryConfig.parse(parser)

        # Assert
        assert config.dict_config["broker_heartbeat"] == 30

    def test_default_heartbeat_propagates_to_dict_config(self, empty_config: ConfigParser):
        # Arrange

        # Act
        config = CeleryConfig.parse(empty_config)

        # Assert
        assert config.dict_config["broker_heartbeat"] == 120
