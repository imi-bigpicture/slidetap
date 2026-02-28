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

import RestoreIcon from '@mui/icons-material/Restore'
import { IconButton, Stack } from '@mui/material'
import React from 'react'

import ClearIcon from '@mui/icons-material/Clear'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import { ValueDisplayType } from 'src/models/value_display_type'
import ValueMenu from './value_menu'

interface AttributeValueControlsProps {
  attribute: Attribute<AttributeValueTypes>
  valueToDisplay: ValueDisplayType
  setValueToDisplay: (value: ValueDisplayType) => void
  handleClear: () => void
  handleReset: () => void
}

export default function AttributeValueControls({
  attribute,
  valueToDisplay,
  setValueToDisplay,
  handleClear,
  handleReset,
}: AttributeValueControlsProps): React.ReactElement {
  return (
    <Stack direction="row" spacing={0.25} alignItems="center">
      <ValueMenu
        attribute={attribute}
        valueToDisplay={valueToDisplay}
        setValueToDisplay={setValueToDisplay}
      />
      <IconButton
        size="small"
        onClick={handleClear}
        disabled={attribute.updatedValue === null}
        title="Clear value"
        sx={{
          border: 1,
          borderColor: 'action.disabled',
          padding: 0.25,
        }}
      >
        <ClearIcon fontSize="inherit" />
      </IconButton>
      <IconButton
        size="small"
        onClick={handleReset}
        disabled={attribute.updatedValue === null}
        title="Reset value"
        sx={{
          border: 1,
          borderColor: 'action.disabled',
          padding: 0.25,
        }}
      >
        <RestoreIcon fontSize="inherit" />
      </IconButton>
    </Stack>
  )
}
