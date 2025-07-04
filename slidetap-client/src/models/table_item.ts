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
import { ImageStatus } from 'src/models/image_status'
import { ProjectStatus } from 'src/models/project_status'


export interface TableItem {
  readonly uid: string
}

export interface ProjectTableItem extends TableItem {
  name: string
  status: ProjectStatus
}

export interface MapperTableItem extends TableItem {
  name: string
  attribute: string
  targets: string[]
}

export interface Item extends TableItem {
  identifier: string
  name: string | null
  pseudonym: string | null
  selected: boolean
  valid: boolean
  attributes: Record<string, Attribute<AttributeValueTypes>>
}

export interface Sample extends Item {
  name: string
}

export interface Image extends Item {
  name: string
  status: ImageStatus
  statusMessage: string
}

export interface Annotation extends Item {
  name: string
}

export interface Observation extends Item {
  name: string
}

export interface ColumnFilter  {
  id: string
  value: unknown
}

export interface ColumnSort {
  column: string
  isAttribute: boolean
  descending: boolean
}

export interface TableRequest {
  start: number
  size: number
  identifierFilter: string | null
  attributeFilters: Record<string, string> | null
  statusFilter: number[] | null
  tagFilter: string[] | null
  sorting : ColumnSort[] | null
  included: boolean | null
  valid: boolean | null
}