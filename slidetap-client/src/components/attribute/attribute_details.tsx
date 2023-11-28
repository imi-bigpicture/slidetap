import React, { type ReactElement } from 'react'

import type { Attribute } from 'models/attribute'
import { Card, CardContent, CardHeader } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import DisplayAttribute from 'components/attribute/display_attribute'

interface AttributeDetailsProps {
  attributes: Record<string, Attribute<any, any>>
  handleAttributeOpen: (attribute: Attribute<any, any>) => void
  handleAttributeUpdate?: (attribute: Attribute<any, any>) => void
}

export default function AttributeDetails({
  attributes,
  handleAttributeOpen,
  handleAttributeUpdate,
}: AttributeDetailsProps): ReactElement {
  return (
    <Card>
      <CardHeader title="Attributes" />
      <CardContent>
        {Object.values(attributes).map((attribute) => {
          return (
            <Grid key={attribute.uid}>
              <DisplayAttribute
                key={attribute.uid}
                attribute={attribute}
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
