from tempfile import TemporaryDirectory

import pandas
import pytest
from werkzeug.datastructures import FileStorage

from slides.importer.metadata import CaseIdFileParser, FileParser


@pytest.fixture()
def df():
    data = {"Case ID": ["case 1"], "Block ID": ["block 1"], "Stain": ["stain 1"]}
    yield pandas.DataFrame(data)


@pytest.fixture()
def df_bytes(df: pandas.DataFrame):
    with TemporaryDirectory() as folder:
        filename = folder + "/file.xlsx"
        df.to_excel(filename, index=False)

        with open(filename, "rb") as out:
            yield out.read()


@pytest.mark.unittest
class TestSlidesUtil:
    def test_rename_colums(self, df: pandas.DataFrame):
        # Arrange

        # Act
        df = CaseIdFileParser._rename_colums(df)
        df = CaseIdFileParser._add_columns_if_missing(df)

        # Assert
        for nice_name, column in CaseIdFileParser.COLUMNS.items():
            assert column.camel_case_name in df
            assert nice_name not in df

    def test_dataframe_to_caseIds(self, df_bytes: bytes):
        # Arrange

        # Act
        parsed_file = CaseIdFileParser(df_bytes)

        # Assert
        assert parsed_file.caseIds == ["case 1"]

    @pytest.mark.parametrize(
        "file, expected_result",
        [
            (
                FileStorage(
                    filename="test.xls", content_type=FileParser.CONTENT_TYPES["xls"]
                ),
                True,
            ),
            (
                FileStorage(
                    filename="test.xlsx", content_type=FileParser.CONTENT_TYPES["xlsx"]
                ),
                True,
            ),
            (
                FileStorage(
                    filename="test.xls", content_type=FileParser.CONTENT_TYPES["xlsx"]
                ),
                False,
            ),
            (
                FileStorage(
                    filename="test.xlsx", content_type=FileParser.CONTENT_TYPES["xls"]
                ),
                False,
            ),
            (FileStorage(), False),
            (FileStorage(filename="test"), False),
        ],
    )
    def test_allowed_file(self, file: FileStorage, expected_result: bool):
        # Arrange

        # Act
        allowed = FileParser._allowed_file(file)

        # Assert
        assert allowed == expected_result
