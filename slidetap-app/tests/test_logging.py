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
from collections.abc import Iterator
from uuid import uuid4

import pytest

from slidetap.logging import setup_logging


@pytest.fixture()
def existing_logger() -> Iterator[logging.Logger]:
    logger = logging.getLogger(f"slidetap.test_logging.{uuid4()}")
    yield logger
    logger.disabled = False


@pytest.mark.unittest
class TestSetupLogging:
    def test_loggers_that_exist_before_the_config_keep_working(
        self, existing_logger: logging.Logger
    ):
        # Act
        setup_logging({"version": 1})

        # Assert
        assert not existing_logger.disabled

    def test_the_config_can_still_disable_existing_loggers(
        self, existing_logger: logging.Logger
    ):
        # Act
        setup_logging({"version": 1, "disable_existing_loggers": True})

        # Assert
        assert existing_logger.disabled
