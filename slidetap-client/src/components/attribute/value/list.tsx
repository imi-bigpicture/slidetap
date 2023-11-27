import React from 'react'
import { Button } from '@mui/material'
import type { ListAttribute } from 'models/attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2

interface DisplayListAttributeProps {
  attribute: ListAttribute
  handleChangeAttribute?: (attributeUid: string) => void
}

export default function DisplayListAttribute({
  attribute,
  handleChangeAttribute,
}: DisplayListAttributeProps): React.ReactElement {
  const handleAttributeOpen = (event: React.MouseEvent<HTMLButtonElement>): void => {
    if (handleChangeAttribute === undefined) {
      return
    }
    const attributeUid = event.currentTarget.id
    console.log('handling opening child object attribute', attributeUid)
    handleChangeAttribute(attributeUid)
  }

  return (
    <React.Fragment>
      {attribute.value !== undefined &&
        Object.values(attribute.value).map((childAttribute) => (
          <Grid key={childAttribute.uid}>
            <Button id={childAttribute.uid} onClick={handleAttributeOpen}>
              {childAttribute.schema.displayName}
            </Button>
          </Grid>
        ))}
    </React.Fragment>
  )
}
