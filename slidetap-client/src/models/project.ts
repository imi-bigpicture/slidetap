//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { ProjectStatus } from 'src/models/project_status'


export interface Project {
  readonly uid: string
  readonly name: string
  readonly status: ProjectStatus
  readonly validAttributes: boolean
  readonly schemaUid: string
  readonly datasetUid: string
  readonly rootSchemaUid: string
  readonly attributes: Record<string, Attribute<AttributeValueTypes>>
  readonly created: string
}
