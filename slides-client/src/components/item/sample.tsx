import React from 'react'
import { Stack, TextField } from '@mui/material'
import { Sample } from 'models/items'
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import DisplayAttribute from 'components/attribute/display_attribute'

interface DisplaySampleProps {
  sample: Sample
}

export default function DisplaySampple({
  sample,
}: DisplaySampleProps): React.ReactElement {
  return (
    <React.Fragment>
      <Stack spacing={2}>
        <TextField label="name" value={sample.name} />
        <FormControlLabel
          label="Selected"
          control={<Checkbox value={sample.selected} />}
        />
        <TextField label="Parents" value={sample.parents.join(', ')} />
        <TextField label="Children" value={sample.children.join(', ')} />
        {Object.keys(sample.attributes).map((tag) => (
          <DisplayAttribute
            key={sample.attributes[tag].uid}
            attribute={sample.attributes[tag]}
          />
        ))}
      </Stack>
    </React.Fragment>
  )
}
