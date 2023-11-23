import React from 'react'
import { FormControl, FormLabel, Stack, TextField, Card , CardHeader } from '@mui/material'
import type { ObjectAttribute } from 'models/attribute'
import DisplayAttribute from '../display_attribute'
import { IsObjectAttribute } from 'models/helpers'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  hideLabel?: boolean | undefined
}

export default function DisplayObjectAttribute({
  attribute,
  hideLabel,
}: DisplayObjectAttributeProps): React.ReactElement {
  const [childObjectOpen, setChildObjectOpen] = React.useState(false)
  const [childObject, setchildObject] = React.useState<ObjectAttribute | undefined>(undefined)

  const handleAttributeOpen = (event: React.MouseEvent<HTMLDivElement>): void => {
    console.log("handle open", event.target.id)
    if (attribute.value === undefined) {
      console.log("no value")
      return
    }
    const attributeUid = event.target.id
    const childObject = Object.values(attribute.value).find((childAttribute) => childAttribute.uid === attributeUid )
    console.log(Object.values(attribute.value))
    setchildObject(childObject)
    setChildObjectOpen(true)
    console.log("childObject", childObject)
  }
  return (
    <Grid container spacing={1} direction="row">
      <Grid xl={6}>
        <Card variant="outlined" >
          <CardHeader title={attribute.schema.displayName} />

          <FormControl component="fieldset" variant="standard">
            {attribute.value !== undefined && Object.values(attribute.value)
              .map((childAttribute) => {
                if (IsObjectAttribute(childAttribute)) {
                  return(
                      <FormControl component="fieldset" variant="standard">
                      {hideLabel !== true && (
                        <FormLabel component="legend">{childAttribute.schema.displayName}</FormLabel>
                      )}
                      <Stack spacing={2} direction="row" sx={{ margin: 2 }}>
                        <TextField value={childAttribute.displayValue} id={ childAttribute.uid } onClick={handleAttributeOpen}/>
                      </Stack>
                  </FormControl>)
                }
                return <DisplayAttribute key={childAttribute.uid} attribute={childAttribute} hideLabel={ false } />
              })}
            </FormControl>
          </Card>
      </Grid>
      {(childObjectOpen && childObject) && (
        <Grid xl={6}>
          <DisplayObjectAttribute attribute={childObject} />
        </Grid>
      )}
    </Grid>
  )
}
