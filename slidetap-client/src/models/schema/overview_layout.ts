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

import type { Breakpoint } from 'src/models/schema/attribute_schema'

export interface OverviewSectionLayout {
  schemaUid: string
  path: string[]
  attributes: string[]
  privateAttributes: string[]
  /** Attributes of the item the section groups by, shown in the same card. */
  parentAttributes: string[]
  displayName: string
  reassignable: boolean
  /** Attributes that may be dragged on their own. Empty means all of them. */
  reassignableAttributes: string[]
  creatable: boolean
  copyable: boolean
  deletable: boolean
  defaultCollapsed: string[]
  width: Partial<Record<Breakpoint, number>>
  /** Move the section out of the main grid into a column beside it, which
   * scrolls on its own. Several sections may set this and they stack in the one
   * column; its width is the first of their `width`s, out of twelve. Below the
   * `md` breakpoint the two columns become one. */
  aside: boolean
  expand: boolean
}

export interface OverviewLayout {
  uid: string
  name: string
  displayName: string
  schemaUid: string
  sections: OverviewSectionLayout[]
}
