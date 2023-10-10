import React from 'react'
import { Stack, TextField } from '@mui/material'
import type { Image } from 'models/items'
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import DisplayAttribute from 'components/attribute/display_attribute'

interface DisplayImageProps {
  image: Image
}

export default function DisplayImage({ image }: DisplayImageProps): React.ReactElement {
  return (
    <React.Fragment>
      <Stack spacing={2}>
        <TextField label="name" value={image.name} />
        <FormControlLabel
          label="Selected"
          control={<Checkbox value={image.selected} />}
        />
        <TextField label="Samples" value={image.samples.join(', ')} />
        <TextField label="Status" value={image.status} />
        {Object.keys(image.attributes.attributes).map((tag) => (
          <DisplayAttribute
            key={image.attributes[tag].uid}
            attribute={image.attributes[tag]}
          />
        ))}
      </Stack>
    </React.Fragment>
  )
}
