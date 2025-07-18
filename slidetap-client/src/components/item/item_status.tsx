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
import { ItemDetailAction } from 'src/models/action'
import type { Item } from 'src/models/item'

interface DisplayItemStatusProps {
  item: Item
  action: ItemDetailAction
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
        label="Attributes"
        control={<Radio size="small" readOnly={true} />}
        checked={item.validAttributes}
      />
      <FormControlLabel
        label="Relations"
        control={<Radio size="small" readOnly={true} />}
        checked={item.validRelations}
      />
      <FormControlLabel
        label="Recycled"
        control={
          action === ItemDetailAction.VIEW ? (
            <Radio size="small" readOnly={true} />
          ) : (
            <Checkbox size="small" />
          )
        }
        checked={!item.selected}
        onChange={(_, value) => {
          if (action === ItemDetailAction.VIEW) {
            return
          }
          handleSelectedUpdate(!value)
        }}
      />
    </Stack>
  )
}
