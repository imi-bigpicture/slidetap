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

import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { Accordion, AccordionDetails, AccordionSummary } from '@mui/material'
import type { Action } from 'models/action'
import { type Attribute, type ObjectAttribute } from 'models/attribute'
import { AttributeSchema, ObjectAttributeSchema } from 'models/schema/attribute_schema'
import { ValueDisplayType } from 'models/value_display_type'
import React from 'react'
import AttributeDetails from '../attribute_details'
import { selectValueToDisplay } from './value_to_display'

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  schema: ObjectAttributeSchema
  action: Action
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
    attribute: Attribute<any>,
    updateAttribute: (tag: string, attribute: Attribute<any>) => Attribute<any>,
  ) => void
  handleAttributeUpdate: (tag: string, attribute: ObjectAttribute) => void
}

export default function DisplayObjectAttribute({
  attribute,
  schema,
  action,
  displayAsRoot,
  valueToDisplay,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayObjectAttributeProps): React.ReactElement {
  const [expanded, setExpanded] = React.useState<boolean>(true)

  const handleOwnAttributeUpdate = (
    tag: string,
    updatedAttribute: Attribute<any>,
  ): ObjectAttribute => {
    const updated = { ...attribute }
    if (updated.updatedValue === undefined) {
      updated.updatedValue = {}
    }
    updated.updatedValue[tag] = updatedAttribute
    return updated
  }
  const handleNestedAttributeUpdate = (
    tag: string,
    attribute: Attribute<any>,
  ): void => {
    const updated = handleOwnAttributeUpdate(tag, attribute)
    handleAttributeUpdate(schema.tag, updated)
  }
  const value = selectValueToDisplay(attribute, valueToDisplay)
  if (displayAsRoot === true) {
    return (
      <AttributeDetails
        schemas={schema.attributes}
        attributes={value}
        action={action}
        spacing={1}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleNestedAttributeUpdate}
      />
    )
  }
  if (value !== undefined && Object.values(value).length === 0) {
    return <div></div>
  }
  return (
    <div>
      <Accordion
        expanded={expanded}
        onChange={() => {
          setExpanded(!expanded)
        }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          {schema.displayName} {expanded ? '' : '- ' + attribute.displayValue}
        </AccordionSummary>
        <AccordionDetails>
          <AttributeDetails
            schemas={schema.attributes}
            attributes={value}
            action={action}
            spacing={1}
            handleAttributeOpen={handleAttributeOpen}
            handleAttributeUpdate={handleNestedAttributeUpdate}
          />
        </AccordionDetails>
      </Accordion>
    </div>
  )
}
