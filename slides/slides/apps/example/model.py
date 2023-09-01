"""Models used for de-serializing input json."""
from typing import Any, Mapping, Union
from marshmallow import Schema, fields
from werkzeug.datastructures import FileStorage


class SpecimenModel(Schema):
    identifier = fields.String()
    collection = fields.String()
    fixation = fields.String()


class BlockModel(Schema):
    identifier = fields.String()
    specimen_identifiers = fields.List(fields.String())
    sampling = fields.String()
    embedding = fields.String()


class SlideModel(Schema):
    identifier = fields.String()
    block_identifier = fields.String()
    primary_stain = fields.String()
    secondary_stain = fields.String()


class ImageModel(Schema):
    identifier = fields.String()
    slide_identifier = fields.String()


class ContainerModel(Schema):
    specimens = fields.List(fields.Nested(SpecimenModel))
    blocks = fields.List(fields.Nested(BlockModel))
    slides = fields.List(fields.Nested(SlideModel))
    images = fields.List(fields.Nested(ImageModel))


def parse_file(file: Union[FileStorage, bytes]) -> Mapping[str, Any]:
    if isinstance(file, FileStorage):
        input = file.stream.read().decode()
    else:
        with open(file, "r") as input_file:
            input = input_file.read()

    container = ContainerModel().loads(input)
    assert isinstance(container, Mapping)
    return container
