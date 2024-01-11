import React, { type ReactElement } from 'react'

import type { Attribute } from 'models/attribute'
import { Card, CardContent } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import DisplayAttribute from 'components/attribute/display_attribute'
import type { Action } from 'models/table_item'

interface AttributeDetailsProps {
  attributes: Record<string, Attribute<any, any>>
  action: Action
  handleAttributeOpen: (attribute: Attribute<any, any>) => void
  handleAttributeUpdate?: (attribute: Attribute<any, any>) => void
}

export default function AttributeDetails({
  attributes,
  action,
  handleAttributeOpen,
  handleAttributeUpdate,
}: AttributeDetailsProps): ReactElement {
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
