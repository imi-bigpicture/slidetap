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

import React from 'react'
import type { ItemDetailAction } from 'src/models/action'
import {
  AttributeValueTypes,
  UnionAttribute,
  type Attribute,
} from 'src/models/attribute'
import {
  AttributeSchema,
  UnionAttributeSchema,
} from 'src/models/schema/attribute_schema'
import { ValueDisplayType } from 'src/models/value_display_type'
import DisplayAttribute from '../display_attribute'
import { selectValueToDisplay } from './value_to_display'

interface DisplayUnionAttributeProps {
  attribute: UnionAttribute
  schema: UnionAttributeSchema
  action: ItemDetailAction
  displayAsRoot?: boolean
  valueToDisplay: ValueDisplayType
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  handleAttributeOpen: (
    schema: AttributeSchema,
    attribute: Attribute<AttributeValueTypes>,
    updateAttribute: (
      tag: string,
      attribute: Attribute<AttributeValueTypes>,
    ) => Attribute<AttributeValueTypes>,
  ) => void
  handleAttributeUpdate: (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ) => void
}

export default function DisplayUnionAttribute({
  attribute,
  schema,
  action,
  displayAsRoot,
  valueToDisplay,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayUnionAttributeProps): React.ReactElement {
  const value = selectValueToDisplay(attribute, valueToDisplay)
  const valueSchema = schema.attributes.find(
    (childSchema) => childSchema.uid === value?.schemaUid,
  )
  if (value === null || valueSchema === undefined) {
    return <></>
  }

  return (
    <DisplayAttribute
      attribute={value}
      schema={valueSchema}
      action={action}
      handleAttributeOpen={handleAttributeOpen}
      handleAttributeUpdate={handleAttributeUpdate}
      displayAsRoot={displayAsRoot}
    />
  )
}
