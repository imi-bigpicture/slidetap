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

from typing import List

from pydantic import BaseModel


class ObservationModel(BaseModel):
    name: str
    identifier: str
    case_identifier: str
    diagnose: str
    report: str


class PatientModel(BaseModel):
    name: str
    identifier: str
    sex: str


class CaseModel(BaseModel):
    name: str
    identifier: str
    patient_identifier: str


class SpecimenModel(BaseModel):
    name: str
    identifier: str
    case_identifier: str
    collection: str
    fixation: str


class BlockModel(BaseModel):
    name: str
    identifier: str
    specimen_identifiers: List[str]
    sampling: str
    embedding: str


class SlideModel(BaseModel):
    name: str
    identifier: str
    block_identifier: str
    primary_stain: str
    secondary_stain: str


class ImageModel(BaseModel):
    name: str
    identifier: str
    slide_identifier: str


class ContainerModel(BaseModel):
    observations: List[ObservationModel]
    patients: List[PatientModel]
    cases: List[CaseModel]
    specimens: List[SpecimenModel]
    blocks: List[BlockModel]
    slides: List[SlideModel]
    images: List[ImageModel]
