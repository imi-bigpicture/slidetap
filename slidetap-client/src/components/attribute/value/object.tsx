import React from 'react'
import { Button } from '@mui/material'
import type { ObjectAttribute } from 'models/attribute'
import DisplayAttribute from '../display_attribute'
import { IsObjectAttribute } from 'models/helpers'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  hideLabel?: boolean | undefined
  handleChangeAttribute?: (attributeUid: string) => void
}

export default function DisplayObjectAttribute({
  attribute,
  hideLabel,
  handleChangeAttribute
}: DisplayObjectAttributeProps): React.ReactElement {

  const handleAttributeOpen = (event: React.MouseEvent<HTMLButtonElement>): void => {
    if (handleChangeAttribute === undefined) {
      return
    }
    const attributeUid = event.target.id
    console.log("handling opening child object attribute", attributeUid)
    handleChangeAttribute(attributeUid)
  }

  return (
    <React.Fragment>
        {attribute.value !== undefined && Object.values(attribute.value)
            .map((childAttribute) => {
              if (IsObjectAttribute(childAttribute)) {
                return <Grid>
                  <Button id={childAttribute.uid} onClick={handleAttributeOpen}>{childAttribute.schema.displayName}</Button>
                </Grid>
              }
              return <Grid>
                <DisplayAttribute key={childAttribute.uid} attribute={childAttribute} hideLabel={false} />
                </Grid>
            })}
    </React.Fragment>
  )
}
