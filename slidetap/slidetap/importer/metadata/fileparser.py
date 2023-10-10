"""Parsing of excel files."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Type, Union

import pandas
from werkzeug.datastructures import FileStorage


class FileParser:
    """Class for opening uploaded xls and xlsx FileStorage file and parsing
    it to list of case ids."""

    @dataclass
    class Column:
        """Specifies camel case name for columns in uploaded file, if
        the column is required to be present in the file, and optionally
        a default value (default to None)."""

        camel_case_name: str
        required: bool
        data_type: Type

    COLUMNS: Dict[str, Column]

    """Maps input column name to column specification."""

    CONTENT_TYPES = {
        "xls": "application/vnd.ms-excel",
        "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    }
    """Maps file extension to content type."""

    def __init__(self, file: Union[FileStorage, bytes]):
        """Parses a xls or xlsx FileStorage (or bytes) to a pandas dataframe.

        Parameters
        ----------
        file: Union[FileStorage, bytes]
            FileStorage or bytes of xls or xlsx file.

        """
        self._filename = ""
        if isinstance(file, FileStorage):
            if not self._allowed_file(file):
                raise ValueError("File is of wrong type.")
            if file.filename is not None:
                self._filename = Path(file.filename).stem
        self._df = self._parse_dataframe(file)
        self._validate_dataframe(self._df)
        self._df = self._rename_colums(self._df)
        self._df = self._add_columns_if_missing(self._df)

    @staticmethod
    def _to_value_or_none(value: Any) -> Any:
        if isinstance(value, float) and math.isnan(value):
            value = None
        return value

    @classmethod
    def _allowed_file(cls, file: FileStorage) -> bool:
        """Return True if file is of allowed type (by file extension and
        content type.

        Parameters
        ----------
        file: FileStorage
            File to check.

        Returns
        ----------
        bool
            True if file is of allowed type.
        """
        ALLOWED_EXTENSIONS = {
            extension: cls.CONTENT_TYPES[extension] for extension in cls.CONTENT_TYPES
        }
        if file.filename is None or "." not in file.filename:
            return False
        extension = file.filename.rsplit(".", 1)[1].lower()
        return (
            extension in ALLOWED_EXTENSIONS
            and file.content_type in ALLOWED_EXTENSIONS[extension]
        )

    @staticmethod
    def _parse_dataframe(file: Union[FileStorage, bytes]) -> pandas.DataFrame:
        """Parse file to pandas dataframe.

        Parameters
        ----------
        file: Union[FileStorage, bytes]
            File to check.

        Returns
        ----------
        pandas.DataFrame
            Content of file as dataframe.
        """
        df = pandas.read_excel(file, header=0, dtype=str)  # type: ignore
        return df

    @classmethod
    def _validate_dataframe(cls, df: pandas.DataFrame):
        """Return true if dataframe contains all required columns.

        Parameters
        ----------
        df: pandas.DataFrame
            Dataframe to check.

        Returns
        ----------
        bool
            Return True if dataframe contains all required columns.

        """
        for column_name, column_properties in cls.COLUMNS.items():
            if column_name not in df and column_properties.required:
                raise ValueError(f"File must have a '{column_name}' column.")

    @classmethod
    def _rename_colums(cls, df: pandas.DataFrame) -> pandas.DataFrame:
        """Rename columns in dataframe to snake case.

        Parameters
        ----------
        df: pandas.DataFrame
            Dataframe to rename.

        Returns
        ----------
        pandas.DataFrame
            Dataframe with renamed columns.
        """
        rename_dictionary = {
            column: column_property.camel_case_name
            for column, column_property in cls.COLUMNS.items()
        }
        return df.rename(columns=rename_dictionary, errors="ignore")  # type: ignore

    @classmethod
    def _add_columns_if_missing(cls, df: pandas.DataFrame) -> pandas.DataFrame:
        """Add columns missing columns to the dataframe. Sets value of missing
        columns to None.

        Parameters
        ----------
        df: pandas.DataFrame
            Dataframe to add missing columns to.

        Returns
        ----------
        pandas.DataFrame
            Dataframe with added columns.
        """
        for column in cls.COLUMNS.values():
            if column.camel_case_name not in df:
                df[column.camel_case_name] = None
        return df


class CaseIdFileParser(FileParser):
    COLUMNS = {"Case ID": FileParser.Column("caseId", True, str)}

    @property
    def caseIds(self) -> List[str]:
        """Return case ids of parsed file."""
        return [
            self._to_value_or_none(row.caseId) for label, row in self._df.iterrows()
        ]


class ImageIdFileParser(FileParser):
    COLUMNS = {"Image ID": FileParser.Column("imageId", True, str)}

    @property
    def imageIds(self) -> List[str]:
        """Return image ids of parsed file."""
        return [
            self._to_value_or_none(row.imageId) for label, row in self._df.iterrows()
        ]
