//    Copyright 2026 SECTRA AB
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

import type {
  Attribute,
  AttributeValueTypes,
  ObjectAttribute,
} from 'src/models/attribute'
import { ValueDisplayType } from 'src/models/value_display_type'
import { selectValueToDisplay } from './value_to_display'

/**
 * An object attribute with one of the attributes it holds edited.
 *
 * The edit is made on what the object holds as shown - what was edited, else
 * what was mapped, else what was imported - so the attributes not edited keep
 * what was mapped of them. Started from what was imported, every attribute
 * beside the edited one would show its imported value, unmapped, from then on.
 * The object is copied, not changed in place, as it is the one being shown.
 */
export function withHeldAttributeUpdated(
  attribute: ObjectAttribute,
  tag: string,
  updatedAttribute: Attribute<AttributeValueTypes>,
): ObjectAttribute {
  const current = selectValueToDisplay(attribute, ValueDisplayType.CURRENT) ?? {}
  return { ...attribute, updatedValue: { ...current, [tag]: updatedAttribute } }
}
