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

"""Module containing interfaces for importing and exporting images and metadata."""
from slidetap.external_interfaces.auth import AuthInterface
from slidetap.external_interfaces.image_export import ImageExportInterface
from slidetap.external_interfaces.image_import import ImageImportInterface
from slidetap.external_interfaces.mapper_injector import MapperInjectorInterface
from slidetap.external_interfaces.metadata_export import MetadataExportInterface
from slidetap.external_interfaces.metadata_import import (
    MetadataImportInterface,
    MetadataSearchParameterType,
)
from slidetap.external_interfaces.pseudonym_factory import PseudonymFactoryInterface
from slidetap.external_interfaces.schema import SchemaInterface

__all__ = [
    "AuthInterface",
    "ImageImportInterface",
    "ImageExportInterface",
    "MetadataImportInterface",
    "MetadataExportInterface",
    "MetadataSearchParameterType",
    "MapperInjectorInterface",
    "PseudonymFactoryInterface",
    "SchemaInterface",
]
