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

import pytest
from slidetap.config import CeleryConfig, ConfigParser


def make_parser(config: dict, broker_url: str = "amqp://localhost") -> ConfigParser:
    """Helper to create a ConfigParser with an injected broker URL."""
    parser = ConfigParser(config=config)
    # Patch get_env so tests don't require environment variables
    parser.get_env = lambda key, default=None: broker_url if key == "SLIDETAP_BROKER_URL" else default  # type: ignore[method-assign]
    return parser


@pytest.mark.unittest
class TestCeleryConfigBrokerHeartbeat:
    def test_default_heartbeat_when_no_celery_section(self):
        # No 'celery' key in config → CeleryConfig uses field default (120)
        parser = make_parser({})
        config = CeleryConfig.parse(parser)
        assert config.broker_heartbeat == 120

    def test_default_heartbeat_when_celery_section_omits_key(self):
        # 'celery' section exists but omits broker_heartbeat → default 120
        parser = make_parser({"celery": {"concurrency": 2}})
        config = CeleryConfig.parse(parser)
        assert config.broker_heartbeat == 120

    def test_custom_heartbeat_value(self):
        # Explicit value in config is used
        parser = make_parser({"celery": {"broker_heartbeat": 60}})
        config = CeleryConfig.parse(parser)
        assert config.broker_heartbeat == 60

    def test_heartbeat_zero_disables_heartbeat(self):
        # 0 is a valid value (disables heartbeat in Celery/AMQP)
        parser = make_parser({"celery": {"broker_heartbeat": 0}})
        config = CeleryConfig.parse(parser)
        assert config.broker_heartbeat == 0

    def test_heartbeat_propagates_to_dict_config(self):
        # The value is passed through to the Celery dict config
        parser = make_parser({"celery": {"broker_heartbeat": 30}})
        config = CeleryConfig.parse(parser)
        assert config.dict_config["broker_heartbeat"] == 30

    def test_default_heartbeat_propagates_to_dict_config(self):
        parser = make_parser({})
        config = CeleryConfig.parse(parser)
        assert config.dict_config["broker_heartbeat"] == 120
