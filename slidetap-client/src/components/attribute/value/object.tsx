import React from 'react'
import { Button } from '@mui/material'
import type { Attribute, ObjectAttribute } from 'models/attribute'
import DisplayAttribute from '../display_attribute'
import { isObjectAttribute } from 'models/helpers'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  hideLabel?: boolean | undefined
  handleAttributeOpen?: (attribute: Attribute<any, any>) => void
}

export default function DisplayObjectAttribute({
  attribute,
  hideLabel,
  handleAttributeOpen,
}: DisplayObjectAttributeProps): React.ReactElement {
  return (
    <React.Fragment>
      {attribute.value !== undefined &&
        Object.values(attribute.value).map((childAttribute) => {
          return (
            <Grid key={childAttribute.uid}>
              <DisplayAttribute
                key={childAttribute.uid}
                attribute={childAttribute}
                hideLabel={false}
                handleAttributeOpen={handleAttributeOpen}
                complexAttributeAsButton={true}
              />
            </Grid>
          )
        })}
    </React.Fragment>
  )
}
