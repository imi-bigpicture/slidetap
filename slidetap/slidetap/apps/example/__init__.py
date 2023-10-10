"""Module containing an example application


The application has a simple schema (defined in `schema.py`) consisting of specimen,
block, slide, and image, with a few attributes.

The metadata importer parses metadata in json format using the models defined in `model.py`.

Images are "imported" from a specified folder.

Metadata are exported as json.
"""
from slidetap.apps.example.app import create_app
from slidetap.apps.example.schema import ExampleSchema
