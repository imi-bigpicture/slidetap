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

"""Config for example application."""

from pathlib import Path

from slidetap.config import CeleryConfig, Config, ConfigParser, DicomizationConfig


class ExampleConfig(Config):
    def _parse(self, parser: ConfigParser):
        super()._parse(parser)
        self._example_test_data_path = Path(
            parser.get_yaml_or_default("example_test_data", "tests/test_data")
        )
        self._example_test_data_image_extension = parser.get_yaml_or_default(
            "example_test_data_image_extension", ".svs"
        )

    @property
    def example_test_data_path(self) -> Path:
        return self._example_test_data_path

    @property
    def example_test_data_image_extension(self) -> str:
        return self._example_test_data_image_extension


class ExampleConfigTest(ExampleConfig):
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
        self._example_test_data_path = Path("tests/test_data")
        self._example_test_data_image_extension = ".svs"
