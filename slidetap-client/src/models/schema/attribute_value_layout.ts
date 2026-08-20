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

import type { AttributeValueField } from 'src/models/table_item'

/**
 * An attribute to show, and which of its values to show.
 *
 * Shared by the views that name the attributes they show one by one, rather
 * than showing whatever an item happens to carry.
 */
export interface AttributeValueLayout {
  tag: string
  /** The mapped value is what the item means; the mappable one is what it was
   * given as, which is what the systems it came from show. */
  field: AttributeValueField
}
