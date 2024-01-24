import { Checkbox, FormControlLabel, Radio, Stack } from '@mui/material'
import { Action } from 'models/action'
import type { ItemDetails } from 'models/item'
import React from 'react'

interface DisplayItemStatusProps {
  item: ItemDetails
  action: Action
  handleSelectedUpdate: (selected: boolean) => void
}

export default function DisplayItemStatus({
  item,
  action,
  handleSelectedUpdate,
}: DisplayItemStatusProps): React.ReactElement {
  return (
    <Stack spacing={1} direction="row" justifyContent="space-evenly">
      <FormControlLabel
        label="Valid"
        control={<Radio readOnly={true} />}
        checked={item.valid}
      />
      <FormControlLabel
        label="Recycled"
        control={action === Action.VIEW ? <Radio readOnly={true} /> : <Checkbox />}
        checked={!item.selected}
        onChange={(event, value) => {
          if (action === Action.VIEW) {
            return
          }
          handleSelectedUpdate(!value)
        }}
      />
    </Stack>
  )
}
