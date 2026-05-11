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

import type { Attribute, AttributeValueTypes } from './attribute'

export interface OverviewItem {
  itemUid: string
  identifier: string
  pseudonym: string | null
  attributes: Record<string, Attribute<AttributeValueTypes>>
  privateAttributes: Record<string, Attribute<AttributeValueTypes>>
}

export interface OverviewSection {
  itemUid: string
  label: string
  pseudonym: string | null
  schemaUid: string
  items: OverviewItem[]
}

export interface OverviewRoot {
  itemUid: string
  identifier: string
  pseudonym: string | null
  batchUid: string
  sections: OverviewSection[]
  previousUid: string | null
  nextUid: string | null
}
