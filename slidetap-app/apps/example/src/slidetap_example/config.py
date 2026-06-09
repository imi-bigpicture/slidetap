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

from dataclasses import dataclass
from pathlib import Path

from slidetap.config import ConfigParser


@dataclass(frozen=True)
class ExampleConfig:
    example_test_data_path: Path
    example_test_data_image_extension: str = ".svs"

    @classmethod
    def parse(cls, parser: ConfigParser) -> "ExampleConfig":
        example_test_data_path = Path(
            parser.get_yaml_or_default("example_test_data", "tests/test_data")
        )
        example_test_data_image_extension = parser.get_yaml_or_default(
            "example_test_data_image_extension", ".svs"
        )
        return cls(
            example_test_data_path=example_test_data_path,
            example_test_data_image_extension=example_test_data_image_extension,
        )
