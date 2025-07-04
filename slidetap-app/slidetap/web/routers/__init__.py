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

from .attribute_router import attribute_router
from .batch_router import batch_router
from .dataset_router import dataset_router
from .image_router import image_router
from .item_router import item_router
from .login_router import login_router
from .mapper_router import mapper_router
from .project_router import project_router
from .schema_router import schema_router
from .tag_router import tag_router

__all__ = [
    "attribute_router",
    "batch_router",
    "dataset_router",
    "image_router",
    "item_router",
    "login_router",
    "mapper_router",
    "project_router",
    "schema_router",
    "tag_router",
]
