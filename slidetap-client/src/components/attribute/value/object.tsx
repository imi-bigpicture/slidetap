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

import { Box, Stack } from '@mui/material'
import React from 'react'
import type { ItemDetailAction } from 'src/models/action'
import {
  AttributeValueTypes,
  RejectedValues,
  type Attribute,
  type ObjectAttribute,
} from 'src/models/attribute'
import { ObjectAttributeSchema } from 'src/models/schema/attribute_schema'
import { ValueDisplayType } from 'src/models/value_display_type'
import AttributeDetails from '../attribute_details'
import AttributeValueControls from '../attribute_value_controls'
import DisplayMappableValue from '../display_mappable_value'
import OutlinedFormControl from '../outlined_form_control'
import { selectValueToDisplay } from './value_to_display'

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  schema: ObjectAttributeSchema
  action: ItemDetailAction
  displayAsRoot?: boolean
  valueToDisplay: ValueDisplayType
  setValueToDisplay: (valueDisplayType: ValueDisplayType) => void
  handleAttributeUpdate: (tag: string, attribute: ObjectAttribute) => void
}

export default function DisplayObjectAttribute({
  attribute,
  schema,
  action,
  displayAsRoot,
  valueToDisplay,
  setValueToDisplay,
  handleAttributeUpdate,
}: DisplayObjectAttributeProps): React.ReactElement {
  const handleOwnAttributeUpdate = (
    tag: string,
    updatedAttribute: Attribute<AttributeValueTypes>,
  ): ObjectAttribute => {
    const updated = { ...attribute }
    if (updated.updatedValue === null) {
      if (updated.originalValue === null) {
        updated.updatedValue = {}
      } else {
        updated.updatedValue = updated.originalValue
      }
    }
    updated.updatedValue[tag] = updatedAttribute
    return updated
  }
  const handleNestedAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    const updated = handleOwnAttributeUpdate(tag, attribute)
    handleAttributeUpdate(schema.tag, updated)
  }
  const handleClear = (): void => {
    handleAttributeUpdate(schema.tag, { ...attribute, updatedValue: null })
  }
  const handleRejectedUpdate = (rejected: RejectedValues): void => {
    handleAttributeUpdate(schema.tag, { ...attribute, rejected })
  }
  const value = selectValueToDisplay(attribute, valueToDisplay)
  const showMappable = valueToDisplay === ValueDisplayType.MAPPABLE
  if (displayAsRoot === true) {
    // No frame to hang the controls off as a right label, so they go above the
    // nested attributes. Without them a mapped object gives no sign of it.
    return (
      <Stack spacing={1}>
        {!schema.readOnly && (
          <Stack direction="row" sx={{ justifyContent: 'flex-end' }}>
            <AttributeValueControls
              attribute={attribute}
              valueToDisplay={valueToDisplay}
              setValueToDisplay={setValueToDisplay}
              handleClear={handleClear}
              handleRejectedUpdate={handleRejectedUpdate}
            />
          </Stack>
        )}
        {showMappable ? (
          <DisplayMappableValue attribute={attribute} />
        ) : (
          <AttributeDetails
            schemas={schema.attributes}
            attributes={value}
            action={action}
            attributeLayout={schema.attributeLayout}
            spacing={1.25}
            handleAttributeUpdate={handleNestedAttributeUpdate}
          />
        )}
      </Stack>
    )
  }
  if (value !== null && Object.values(value).length === 0) {
    return <div></div>
  }
  return (
    <OutlinedFormControl
      label={schema.displayName}
      required={!schema.optional}
      error={false}
      fullWidth
      rightLabel={
        <AttributeValueControls
          attribute={attribute}
          valueToDisplay={valueToDisplay}
          setValueToDisplay={setValueToDisplay}
          handleClear={handleClear}
          handleRejectedUpdate={handleRejectedUpdate}
        />
      }
    >
      <Box className="outlined-form-control-content" sx={{ width: '100%' }}>
        {showMappable ? (
          // Same top margin the nested attributes get, to clear the label.
          <Box sx={{ mt: 2, width: '100%' }}>
            <DisplayMappableValue attribute={attribute} />
          </Box>
        ) : (
          <AttributeDetails
            schemas={schema.attributes}
            attributes={value}
            action={action}
            attributeLayout={schema.attributeLayout}
            spacing={1.25}
            marginTop={2}
            handleAttributeUpdate={handleNestedAttributeUpdate}
          />
        )}
      </Box>
    </OutlinedFormControl>
  )
}
