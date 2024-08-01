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

"""Models used for de-serializing input json."""

from marshmallow import Schema, fields


class SpecimenModel(Schema):
    name = fields.String()
    identifier = fields.String()
    collection = fields.String()
    fixation = fields.String()


class BlockModel(Schema):
    name = fields.String()
    identifier = fields.String()
    specimen_identifiers = fields.List(fields.String())
    sampling = fields.String()
    embedding = fields.String()


class SlideModel(Schema):
    name = fields.String()
    identifier = fields.String()
    block_identifier = fields.String()
    primary_stain = fields.String()
    secondary_stain = fields.String()


class ImageModel(Schema):
    name = fields.String()
    identifier = fields.String()
    slide_identifier = fields.String()


class ContainerModel(Schema):
    specimens = fields.List(fields.Nested(SpecimenModel))
    blocks = fields.List(fields.Nested(BlockModel))
    slides = fields.List(fields.Nested(SlideModel))
    images = fields.List(fields.Nested(ImageModel))
