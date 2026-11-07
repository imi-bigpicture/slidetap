#    Copyright 2026 SECTRA AB
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

"""How the application behaves, as its plugin is built."""

from slidetap.model.base_model import FrozenBaseModel


class ApplicationPolicy(FrozenBaseModel):
    """How the application behaves, as its plugin is built: the same for every
    project. Not a setting, as a config is, but what the interfaces of the
    plugin say, gathered for the services and the client that go by them. The
    client is given it by ``GET /api/application/policy``."""

    pre_processes_images_separately: bool = True
    """Whether the images of a batch are downloaded and pre-processed, their
    metadata imported from their files, in a step of their own: after the
    batch is curated as searched, and before it is curated for post-processing.
    See :py:attr:`ImageImportInterface.pre_processes_separately`.

    Otherwise a batch goes from the metadata search to curation and
    post-processing, without the pre-processing statuses, and each image is
    downloaded and pre-processed right before it is converted, in the same
    task. What the import leaves for the files to say is then not held against
    an item until the batch is post-processed."""
