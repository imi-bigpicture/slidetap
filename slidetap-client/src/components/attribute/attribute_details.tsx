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

import { Stack } from '@mui/material'
import DisplayAttribute from 'components/attribute/display_attribute'
import type { Action } from 'models/action'
import { type Attribute } from 'models/attribute'
import { type AttributeSchema } from 'models/schema'
import { ValueStatus } from 'models/status'

interface AttributeDetailsProps {
  schemas: AttributeSchema[]
  attributes?: Record<string, Attribute<any, any>>
  action: Action
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  spacing?: number
  handleAttributeOpen: (
    attribute: Attribute<any, any>,
    updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>,
  ) => void
  handleAttributeUpdate: (attribute: Attribute<any, any>) => void
}

export default function AttributeDetails({
  schemas,
  attributes,
  action,
  spacing,
  handleAttributeOpen,
  handleAttributeUpdate,
}: AttributeDetailsProps): React.ReactElement {
  if (spacing === undefined) {
    spacing = 2
  }
  return (
    <Stack direction="column" spacing={spacing}>
      {schemas.map((schema) => {
        let attribute: Attribute<any, any> | undefined
        attribute = attributes?.[schema.tag]
        if (attribute === undefined) {
          if (schema.optional) {
            // TODO show the attributes in edit mode
            return null
          }
          attribute = {
            uid: '',
            schema,
            displayValue: '',
            mappingStatus: ValueStatus.NO_MAPPABLE_VALUE,
            valid: schema.optional,
          }
        }
        return (
          <DisplayAttribute
            key={schema.uid}
            attribute={attribute}
            action={action}
            handleAttributeOpen={handleAttributeOpen}
            handleAttributeUpdate={handleAttributeUpdate}
          />
        )
      })}
    </Stack>
  )
}
