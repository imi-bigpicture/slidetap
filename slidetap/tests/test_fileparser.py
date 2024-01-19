from tempfile import TemporaryDirectory

import pandas
import pytest
from werkzeug.datastructures import FileStorage

from slidetap.importer.metadata import CaseIdFileParser, FileParser


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
            yield FileStorage(
                out,
                filename=filename,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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

    def test_dataframe_to_caseIds(self, file: FileStorage):
        # Arrange

        # Act
        parsed_file = CaseIdFileParser(file)

        # Assert
        assert parsed_file.caseIds == ["case 1"]

    @pytest.mark.parametrize(
        "file, expected_result",
        [
            (
                FileStorage(
                    filename="test.xls", content_type=FileParser.CONTENT_TYPES["xls"]
                ),
                "application/vnd.ms-excel",
            ),
            (
                FileStorage(
                    filename="test.xlsx", content_type=FileParser.CONTENT_TYPES["xlsx"]
                ),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                FileStorage(
                    filename="test.xls", content_type=FileParser.CONTENT_TYPES["xlsx"]
                ),
                None,
            ),
            (
                FileStorage(
                    filename="test.xlsx", content_type=FileParser.CONTENT_TYPES["xls"]
                ),
                None,
            ),
            (FileStorage(), None),
            (FileStorage(filename="test"), None),
        ],
    )
    def test_content_type(self, file: FileStorage, expected_result: str):
        # Arrange

        # Act
        content_type = FileParser._get_content_type(file)

        # Assert
        assert content_type == expected_result
