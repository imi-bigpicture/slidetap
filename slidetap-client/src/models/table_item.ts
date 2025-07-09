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
import { Item } from './item'


export interface BaseTableItem {
  readonly uid: string
}

export interface ProjectTableItem extends BaseTableItem {
  name: string
  status: ProjectStatus
}

export interface MapperTableItem extends BaseTableItem {
  name: string
  attribute: string
  targets: string[]
}

export interface TableItem extends BaseTableItem {
  identifier: string
  name: string | null
  pseudonym: string | null
  selected: boolean
  valid: boolean
  attributes: Record<string, Attribute<AttributeValueTypes>>
}

export interface SampleTableItem extends TableItem {
  name: string
}

export interface ImageTableItem extends TableItem {
  name: string
  status: ImageStatus
  statusMessage: string
}

export interface AnnotationTableItem extends TableItem {
  name: string
}

export interface ObservationTableItem extends TableItem {
  name: string
}

export interface ColumnFilter  {
  id: string
  value: unknown
}

export enum SortType {
  IDENTIFIER = "identifier",
  VALID = "valid",
  STATUS = "status",
  MESSAGE = "message",
  ATTRIBUTE = "attribute",
  RELATION = "relation"
}

export interface ColumnSort {
  descending: boolean
  sortType: SortType
}

export interface AttributeSort extends ColumnSort {
  column: string
  sortType: SortType.ATTRIBUTE
}

export interface RelationSort extends ColumnSort {
  relationSchemaUid: string
  relationType: RelationFilterType
  sortType: SortType.RELATION
}

export enum RelationFilterType {
  PARENT = "parent",
  CHILD = "child",
  IMAGE = "image",
  OBSERVATION = "observation",
  ANNOTATION = "annotation",
  SAMPLE = "sample"
}

export interface RelationFilterDefinition {
  title: string
  relationSchemaUid: string
  relationType: RelationFilterType
  valueGetter: (item: Item) => number

}

export interface RelationFilter {
  relationSchemaUid: string
  relationType: RelationFilterType
  minCount: number | null
  maxCount: number | null
}

export interface TableRequest {
  start: number
  size: number
  identifierFilter: string | null
  attributeFilters: Record<string, string> | null
  relationFilters: RelationFilter[] | null
  statusFilter: number[] | null
  tagFilter: string[] | null
  sorting : ColumnSort[] | null
  included: boolean | null
  valid: boolean | null

}