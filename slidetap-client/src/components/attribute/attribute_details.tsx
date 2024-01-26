import React from 'react'

import { Stack } from '@mui/material'
import DisplayAttribute from 'components/attribute/display_attribute'
import type { Action } from 'models/action'
import { type Attribute } from 'models/attribute'

interface AttributeDetailsProps {
  attributes: Record<string, Attribute<any, any>>
  action: Action
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
  handleAttributeUpdate: (attribute: Attribute<any, any>) => void
}

export default function AttributeDetails({
  attributes,
  action,
  handleAttributeOpen,
  handleAttributeUpdate,
}: AttributeDetailsProps): React.ReactElement {
  return (
    <Stack direction="column" spacing={2}>
      {Object.values(attributes).map((attribute) => {
        console.log(attribute.schema.displayName, attribute.valid)
        return (
          <DisplayAttribute
            key={attribute.uid}
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
