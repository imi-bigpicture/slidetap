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

"""Module containing an example application


The application has a simple schema (defined in `schema.py`) consisting of specimen,
block, slide, and image, with a few attributes.

The metadata importer parses metadata in json format using the models defined in `model.py`.

Images are "imported" from a specified folder.

Metadata are exported as json.
"""
from slidetap.apps.example.web_app_factory import create_app
