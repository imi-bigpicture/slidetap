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

import React, { useMemo, useState } from 'react'

import ClearIcon from '@mui/icons-material/Clear'
import RestoreIcon from '@mui/icons-material/Restore'
import { Avatar, Chip, Divider, ListItemIcon, ListItemText, Menu, MenuItem } from '@mui/material'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import { ValueDisplayType } from 'src/models/value_display_type'

interface AttributeValueControlsProps {
  attribute: Attribute<AttributeValueTypes>
  valueToDisplay: ValueDisplayType
  setValueToDisplay: (value: ValueDisplayType) => void
  handleClear: () => void
  handleReset: () => void
}

const displayTypeLabels: Record<ValueDisplayType, string> = {
  [ValueDisplayType.CURRENT]: 'Current',
  [ValueDisplayType.UPDATED]: 'Updated',
  [ValueDisplayType.ORIGINAL]: 'Original',
  [ValueDisplayType.MAPPED]: 'Mapped',
}

const displayTypeShort: Record<ValueDisplayType, string> = {
  [ValueDisplayType.CURRENT]: 'C',
  [ValueDisplayType.UPDATED]: 'U',
  [ValueDisplayType.ORIGINAL]: 'O',
  [ValueDisplayType.MAPPED]: 'M',
}

export default function AttributeValueControls({
  attribute,
  valueToDisplay,
  setValueToDisplay,
  handleClear,
  handleReset,
}: AttributeValueControlsProps): React.ReactElement {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)
  const open = Boolean(anchorEl)

  const availableDisplayTypes = useMemo(() => {
    const types: ValueDisplayType[] = []
    if (attribute.updatedValue !== null) {
      types.push(ValueDisplayType.UPDATED)
    }
    if (attribute.mappedValue !== null) {
      types.push(ValueDisplayType.MAPPED)
    }
    if (attribute.originalValue !== null) {
      types.push(ValueDisplayType.ORIGINAL)
    }
    return types
  }, [attribute.updatedValue, attribute.originalValue, attribute.mappedValue])

  const activeValue = useMemo(() => {
    if (attribute.updatedValue !== null) {
      return ValueDisplayType.UPDATED
    }
    if (attribute.mappedValue !== null) {
      return ValueDisplayType.MAPPED
    }
    if (attribute.originalValue !== null) {
      return ValueDisplayType.ORIGINAL
    }
    return ValueDisplayType.CURRENT
  }, [attribute.updatedValue, attribute.mappedValue, attribute.originalValue])

  const hasActions = attribute.updatedValue !== null
  const hasMenu = hasActions || availableDisplayTypes.length > 1

  return (
    <>
      <Chip
        label={displayTypeShort[valueToDisplay]}
        onClick={hasMenu ? (e) => setAnchorEl(e.currentTarget) : undefined}
        variant={valueToDisplay === activeValue ? 'filled' : 'outlined'}
        clickable={hasMenu}
        disabled={!hasMenu}
        size="small"
      />
      <Menu
        anchorEl={anchorEl}
        open={open}
        onClose={() => setAnchorEl(null)}
        slotProps={{ paper: { sx: { minWidth: 140 } } }}
      >
        {availableDisplayTypes.map((type) => (
          <MenuItem
            key={type}
            dense
            selected={valueToDisplay === type}
            onClick={() => {
              setValueToDisplay(type)
              setAnchorEl(null)
            }}
          >
            <ListItemIcon>
              <Avatar
                sx={{
                  width: 20,
                  height: 20,
                  fontSize: '0.7rem',
                  bgcolor: valueToDisplay === type ? 'primary.main' : 'action.disabled',
                }}
              >
                {displayTypeShort[type]}
              </Avatar>
            </ListItemIcon>
            <ListItemText primaryTypographyProps={{ variant: 'body2' }}>
              {displayTypeLabels[type]}
            </ListItemText>
          </MenuItem>
        ))}
        {hasActions && <Divider />}
        {hasActions && (
          <MenuItem
            dense
            onClick={() => {
              handleClear()
              setAnchorEl(null)
            }}
          >
            <ListItemIcon>
              <ClearIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primaryTypographyProps={{ variant: 'body2' }}>Clear</ListItemText>
          </MenuItem>
        )}
        {hasActions && (
          <MenuItem
            dense
            onClick={() => {
              handleReset()
              setAnchorEl(null)
            }}
          >
            <ListItemIcon>
              <RestoreIcon fontSize="small" />
            </ListItemIcon>
            <ListItemText primaryTypographyProps={{ variant: 'body2' }}>Reset</ListItemText>
          </MenuItem>
        )}
      </Menu>
    </>
  )
}
