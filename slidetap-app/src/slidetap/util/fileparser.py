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

"""Parsing of excel files."""

import io
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Type

import pandas
from slidetap.model import File


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

    def __init__(self, file: File):
        """Parses a xls or xlsx FileStorage (or bytes) to a pandas dataframe.

        Parameters
        ----------
        file: UploadFile
            UploadFile or bytes of xls or xlsx file.

        """

        if file.filename is not None:
            self._filename = Path(file.filename).stem
        else:
            self._filename = ""
        if file.content_type == self.CONTENT_TYPES["csv"]:
            self._df = self._parse_csv_dataframe(file.stream)
        elif (
            file.content_type == self.CONTENT_TYPES["xls"]
            or file.content_type == self.CONTENT_TYPES["xlsx"]
        ):
            self._df = self._parse_excel_dataframe(file.stream)
        else:
            raise ValueError(
                f"Unsupported file type {file.content_type} for file {self._filename}."
            )
        self._validate_dataframe(self._df)
        self._df = self._rename_colums(self._df)
        self._df = self._add_columns_if_missing(self._df)

    @staticmethod
    def _to_value_or_none(value: Any) -> Any:
        if isinstance(value, float) and math.isnan(value):
            value = None
        return value

    @staticmethod
    def _parse_excel_dataframe(data: BinaryIO) -> pandas.DataFrame:
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
        return pandas.read_excel(data, header=0, dtype=str)

    @staticmethod
    def _parse_csv_dataframe(data: BinaryIO) -> pandas.DataFrame:
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
        return pandas.read_csv(data, header=0, dtype=str)

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
