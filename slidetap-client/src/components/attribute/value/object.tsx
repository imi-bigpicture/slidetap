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
import React from 'react'
import AttributeDetails from '../attribute_details'

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  action: Action
  displayAsRoot?: boolean
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  handleAttributeOpen: (
    attribute: Attribute<any, any>,
    updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>,
  ) => void
  handleAttributeUpdate: (attribute: ObjectAttribute) => void
}

export default function DisplayObjectAttribute({
  attribute,
  action,
  displayAsRoot,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayObjectAttributeProps): React.ReactElement {
  const [expanded, setExpanded] = React.useState<boolean>(true)

  const handleOwnAttributeUpdate = (
    updatedAttribute: Attribute<any, any>,
  ): Attribute<any, any> => {
    const updated = { ...attribute }
    if (updated.value === undefined) {
      updated.value = {}
    }
    updated.value[updatedAttribute.schema.tag] = updatedAttribute
    return updated
  }
  const handleNestedAttributeUpdate = (attribute: Attribute<any, any>): void => {
    const updated = handleOwnAttributeUpdate(attribute)
    handleAttributeUpdate(updated)
  }
  if (displayAsRoot === true) {
    return (
      <AttributeDetails
        schemas={attribute.schema.attributes}
        attributes={attribute.value}
        action={action}
        spacing={1}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleNestedAttributeUpdate}
      />
    )
  }
  if (attribute.value !== undefined && Object.values(attribute.value).length === 0) {
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
          {attribute.schema.displayName} {expanded ? '' : '- ' + attribute.displayValue}
        </AccordionSummary>
        <AccordionDetails>
          <AttributeDetails
            schemas={attribute.schema.attributes}
            attributes={attribute.value}
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
