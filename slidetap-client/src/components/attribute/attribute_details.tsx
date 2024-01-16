import React from 'react'

import { Card, CardContent } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import DisplayAttribute from 'components/attribute/display_attribute'
import type { Attribute } from 'models/attribute'
import type { Action } from 'models/table_item'

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
    <Card>
      <CardContent>
        {Object.values(attributes).map((attribute) => {
          return (
            <Grid key={attribute.uid}>
              <DisplayAttribute
                key={attribute.uid}
                attribute={attribute}
                action={action}
                hideLabel={false}
                handleAttributeOpen={handleAttributeOpen}
                handleAttributeUpdate={handleAttributeUpdate}
                complexAttributeAsButton={true}
              />
            </Grid>
          )
        })}
      </CardContent>
    </Card>
  )
}
