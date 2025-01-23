//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import { Checkbox, FormControlLabel, Radio, Stack } from '@mui/material'
import React from 'react'
import { Action } from 'src/models/action'
import type { Item } from 'src/models/item'

interface DisplayItemStatusProps {
  item: Item
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
        label="Valid attributes"
        control={<Radio readOnly={true} />}
        checked={item.validAttributes}
      />
      <FormControlLabel
        label="Valid relations"
        control={<Radio readOnly={true} />}
        checked={item.validRelations}
      />
      <FormControlLabel
        label="Recycled"
        control={action === Action.VIEW ? <Radio readOnly={true} /> : <Checkbox />}
        checked={!item.selected}
        onChange={(_, value) => {
          if (action === Action.VIEW) {
            return
          }
          handleSelectedUpdate(!value)
        }}
      />
    </Stack>
  )
}
