import React from 'react'
import { Button } from '@mui/material'
import type { Attribute, ListAttribute } from 'models/attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2

interface DisplayListAttributeProps {
  attribute: ListAttribute
  handleAttributeOpen?: (
    attribute: Attribute<any, any>,
    parentAttribute?: Attribute<any, any>,
  ) => void
}

export default function DisplayListAttribute({
  attribute,
  handleAttributeOpen,
}: DisplayListAttributeProps): React.ReactElement {
  return (
    <Grid>
      {attribute.value !== undefined &&
        Object.values(attribute.value).map((childAttribute) => (
          <Grid key={childAttribute.uid}>
            <Button
              id={childAttribute.uid}
              onClick={() => {
                if (handleAttributeOpen === undefined) {
                  return
                }
                handleAttributeOpen(childAttribute, attribute)
              }}
            >
              {childAttribute.displayValue}
            </Button>
          </Grid>
        ))}
    </Grid>
  )
}
