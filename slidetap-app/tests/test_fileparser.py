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

import io
from tempfile import TemporaryDirectory
from typing import Tuple

import pandas
import pytest
from slidetap.util.fileparser import CaseIdFileParser, FileParser
from starlette.datastructures import Headers


@pytest.fixture()
def df():
    data = {"Case ID": ["case 1"], "Block ID": ["block 1"], "Stain": ["stain 1"]}
    yield pandas.DataFrame(data)


@pytest.fixture()
def file(df: pandas.DataFrame):
    with TemporaryDirectory() as folder:
        filename = folder + "/file.xlsx"
        df.to_excel(filename, index=False)

        with open(filename, "rb") as out:
            yield (
                out,
                filename,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )


@pytest.mark.unittest
class TestCaseIdFileParser:
    def test_rename_colums(self, df: pandas.DataFrame):
        # Arrange

        # Act
        df = CaseIdFileParser._rename_colums(df)
        df = CaseIdFileParser._add_columns_if_missing(df)

        # Assert
        for nice_name, column in CaseIdFileParser.COLUMNS.items():
            assert column.camel_case_name in df
            assert nice_name not in df

    def test_dataframe_to_caseIds(self, file: Tuple[io.BufferedReader, str, str]):
        # Arrange
        file, filename, content_type = file

        # Act
        parsed_file = CaseIdFileParser(filename, content_type, file)

        # Assert
        assert parsed_file.caseIds == ["case 1"]

    @pytest.mark.parametrize(
        "file, expected_result",
        [
            (
                (io.BytesIO(), "test.xls", FileParser.CONTENT_TYPES["xls"]),
                "application/vnd.ms-excel",
            ),
            (
                (io.BytesIO(), "test.xlsx", FileParser.CONTENT_TYPES["xlsx"]),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                (io.BytesIO(), "test.xls", FileParser.CONTENT_TYPES["xls"]),
                None,
            ),
            (
                (io.BytesIO(), "test.xlsx", FileParser.CONTENT_TYPES["xlsx"]),
                None,
            ),
            (
                (
                    io.BytesIO(),
                    "test.xls",
                    Headers({"Content-Type": FileParser.CONTENT_TYPES["xls"]}),
                ),
                None,
            ),
            # (UploadFile(file=io.BytesIO()), None),
            # (UploadFile(file=io.BytesIO(), filename="test"), None),
        ],
    )
    def test_content_type(
        self, file: Tuple[io.BufferedReader, str, str], expected_result: str
    ):
        # Arrange
        file, filename, content_type = file

        # Act
        content_type = FileParser._get_content_type(filename, content_type, file)

        # Assert
        assert content_type == expected_result
