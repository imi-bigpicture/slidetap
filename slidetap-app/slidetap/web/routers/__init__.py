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

"""FastAPI routers for SlideTap."""

from .attribute_router import AttributeRouter
from .batch_router import BatchRouter
from .dataset_router import DatasetRouter
from .image_router import ImageRouter
from .item_router import ItemRouter
from .login_router import LoginRouter
from .mapper_router import MapperRouter
from .project_router import ProjectRouter
from .router import Router, SecuredRouter
from .schema_router import SchemaRouter

__all__ = [
    "Router",
    "SecuredRouter",
    "AttributeRouter",
    "BatchRouter",
    "DatasetRouter",
    "ImageRouter",
    "ItemRouter",
    "LoginRouter",
    "MapperRouter",
    "ProjectRouter",
    "SchemaRouter",
]
