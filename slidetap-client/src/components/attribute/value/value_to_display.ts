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

import { Attribute, RejectedValues } from 'src/models/attribute'
import { ValueDisplayType } from 'src/models/value_display_type'

/** Whether a source of a value has been refused by a curator. */
export function isRejected<valueType>(
  attribute: Attribute<valueType>,
  source: RejectedValues,
): boolean {
  return ((attribute.rejected ?? RejectedValues.NONE) & source) === source
}

export function selectValueToDisplay<valueType>(
  attribute: Attribute<valueType>,
  valueToDisplay: ValueDisplayType,
): valueType | null {
  if (valueToDisplay === ValueDisplayType.CURRENT) {
    // What was edited, else what was mapped, else what was imported — each of
    // them only if it says something and has not been refused.
    if (attribute.updatedValue !== undefined && attribute.updatedValue !== null) {
      return attribute.updatedValue
    }
    if (
      attribute.mappedValue !== undefined &&
      attribute.mappedValue !== null &&
      !isRejected(attribute, RejectedValues.MAPPABLE)
    ) {
      return attribute.mappedValue
    }
    if (
      attribute.originalValue !== null &&
      !isRejected(attribute, RejectedValues.ORIGINAL)
    ) {
      return attribute.originalValue
    }
    return null
  }
  if (valueToDisplay === ValueDisplayType.ORIGINAL) {
    return attribute.originalValue
  }
  if (valueToDisplay === ValueDisplayType.UPDATED) {
    return attribute.updatedValue
  }
  if (valueToDisplay === ValueDisplayType.MAPPED) {
    return attribute.mappedValue
  }
  return null
}
