"""Parsing of excel files."""

import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

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
        "csv": "text/csv",
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    """Maps file extension to content type."""

    def __init__(self, file: FileStorage):
        """Parses a xls or xlsx FileStorage (or bytes) to a pandas dataframe.

        Parameters
        ----------
        file: FileStorage
            FileStorage or bytes of xls or xlsx file.

        """
        content_type = self._get_content_type(file)
        if content_type is None:
            raise ValueError("File is of wrong type.")
        if file.filename is not None:
            self._filename = Path(file.filename).stem
        else:
            self._filename = ""
        if content_type == "text/csv":
            self._df = self._parse_csv_dataframe(file)
        else:
            self._df = self._parse_excel_dataframe(file)
        self._validate_dataframe(self._df)
        self._df = self._rename_colums(self._df)
        self._df = self._add_columns_if_missing(self._df)

    @staticmethod
    def _to_value_or_none(value: Any) -> Any:
        if isinstance(value, float) and math.isnan(value):
            value = None
        return value

    @classmethod
    def _get_content_type(cls, file: FileStorage) -> Optional[str]:
        """Return content type if file is of allowed type by file extension and
        content type.

        Parameters
        ----------
        file: FileStorage
            File to check.

        Returns
        ----------
        Optional[str]
            Content type of file.
        """
        ALLOWED_EXTENSIONS = {
            extension: cls.CONTENT_TYPES[extension] for extension in cls.CONTENT_TYPES
        }
        if file.filename is None or "." not in file.filename:
            return None
        extension = file.filename.rsplit(".", 1)[1].lower()
        if (
            extension not in ALLOWED_EXTENSIONS
            or file.content_type not in ALLOWED_EXTENSIONS[extension]
        ):
            return None
        return file.content_type

    @staticmethod
    def _parse_excel_dataframe(file: FileStorage) -> pandas.DataFrame:
        """Parse file to pandas dataframe.

        Parameters
        ----------
        file: FileStorage
            File to parse.

        Returns
        ----------
        pandas.DataFrame
            Content of file as dataframe.
        """
        with io.BytesIO(file.stream.read()) as stream:
            return pandas.read_excel(stream, header=0, dtype=str)

    @staticmethod
    def _parse_csv_dataframe(file: FileStorage) -> pandas.DataFrame:
        """Parse file to pandas dataframe.

        Parameters
        ----------
        file: FileStorage
            File to parse.

        Returns
        ----------
        pandas.DataFrame
            Content of file as dataframe.
        """
        with io.BytesIO(file.stream.read()) as stream:
            return pandas.read_csv(stream, header=0, dtype=str)

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
