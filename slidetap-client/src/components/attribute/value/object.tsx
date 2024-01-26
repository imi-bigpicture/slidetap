import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { Accordion, AccordionDetails, AccordionSummary, Stack } from '@mui/material'
import type { Action } from 'models/action'
import { type Attribute, type ObjectAttribute } from 'models/attribute'
import React from 'react'
import DisplayAttribute from '../display_attribute'

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
      <Stack direction="column" spacing={1}>
        {attribute.value !== undefined &&
          Object.values(attribute.value).map((childAttribute) => {
            return (
              <DisplayAttribute
                key={childAttribute.uid}
                action={action}
                attribute={childAttribute}
                handleAttributeOpen={handleAttributeOpen}
                handleAttributeUpdate={handleNestedAttributeUpdate}
              />
            )
          })}
      </Stack>
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
          <Stack direction="column" spacing={1}>
            {attribute.value !== undefined &&
              Object.values(attribute.value).map((childAttribute) => {
                return (
                  <DisplayAttribute
                    key={childAttribute.uid}
                    action={action}
                    attribute={childAttribute}
                    handleAttributeOpen={handleAttributeOpen}
                    handleAttributeUpdate={handleNestedAttributeUpdate}
                  />
                )
              })}
          </Stack>
        </AccordionDetails>
      </Accordion>
    </div>
  )
}
