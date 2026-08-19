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

import BlockIcon from '@mui/icons-material/Block'
import ClearIcon from '@mui/icons-material/Clear'
import UndoIcon from '@mui/icons-material/Undo'
import {
  Avatar,
  Chip,
  Divider,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Tooltip,
} from '@mui/material'
import { isRejected } from 'src/components/attribute/value/value_to_display'
import {
  AttributeValueTypes,
  RejectedValues,
  type Attribute,
} from 'src/models/attribute'
import { ValueDisplayType } from 'src/models/value_display_type'

interface AttributeValueControlsProps {
  attribute: Attribute<AttributeValueTypes>
  valueToDisplay: ValueDisplayType
  setValueToDisplay: (value: ValueDisplayType) => void
  handleClear: () => void
  /** Refuse, or accept again, what the item came in with. */
  handleRejectedUpdate: (rejected: RejectedValues) => void
}

const displayTypeLabels: Record<ValueDisplayType, string> = {
  [ValueDisplayType.CURRENT]: 'Current',
  [ValueDisplayType.UPDATED]: 'Updated value',
  [ValueDisplayType.ORIGINAL]: 'Original value',
  [ValueDisplayType.MAPPED]: 'Mapped value',
  [ValueDisplayType.MAPPABLE]: 'Raw value',
}

const displayTypeShort: Record<ValueDisplayType, string> = {
  [ValueDisplayType.CURRENT]: 'C',
  [ValueDisplayType.UPDATED]: 'U',
  [ValueDisplayType.ORIGINAL]: 'O',
  [ValueDisplayType.MAPPED]: 'M',
  [ValueDisplayType.MAPPABLE]: 'R',
}

export default function AttributeValueControls({
  attribute,
  valueToDisplay,
  setValueToDisplay,
  handleClear,
  handleRejectedUpdate,
}: AttributeValueControlsProps): React.ReactElement {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null)

  const availableDisplayTypes = useMemo(() => {
    const types: ValueDisplayType[] = []
    // The raw value comes first: it is the input to the mapping, the rest are
    // outcomes.
    if (attribute.mappableValue !== null) {
      types.push(ValueDisplayType.MAPPABLE)
    }
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
  }, [
    attribute.updatedValue,
    attribute.mappedValue,
    attribute.mappableValue,
    attribute.originalValue,
  ])

  /** The value the item resolves to, the one an edit or a mapping overrides. */
  const activeValue = useMemo(() => {
    if (attribute.updatedValue !== null) {
      return ValueDisplayType.UPDATED
    }
    if (
      attribute.mappedValue !== null &&
      !isRejected(attribute, RejectedValues.MAPPABLE)
    ) {
      return ValueDisplayType.MAPPED
    }
    if (
      attribute.originalValue !== null &&
      !isRejected(attribute, RejectedValues.ORIGINAL)
    ) {
      return ValueDisplayType.ORIGINAL
    }
    return ValueDisplayType.CURRENT
  }, [
    attribute.updatedValue,
    attribute.mappedValue,
    attribute.originalValue,
    attribute.rejected,
  ])

  const rejected = attribute.rejected ?? RejectedValues.NONE
  const toggleRejected = (source: RejectedValues): void => {
    handleRejectedUpdate(
      isRejected(attribute, source) ? rejected & ~source : rejected | source,
    )
    setAnchorEl(null)
  }
  /** The sources this attribute has, and so can be asked about. */
  const refusable: Array<{ source: RejectedValues; label: string }> = []
  if (attribute.originalValue !== null) {
    refusable.push({ source: RejectedValues.ORIGINAL, label: 'original value' })
  }
  if (attribute.mappableValue !== null) {
    refusable.push({ source: RejectedValues.MAPPABLE, label: 'raw value' })
  }

  // Nothing is pinned until a value is picked, and the field then shows the
  // active value.
  const shownValue =
    valueToDisplay === ValueDisplayType.CURRENT ? activeValue : valueToDisplay
  const hasActions = attribute.updatedValue !== null
  const hasMenu = hasActions || availableDisplayTypes.length > 1 || refusable.length > 0

  return (
    <React.Fragment>
      <Tooltip title={displayTypeLabels[shownValue]}>
        <Chip
          label={displayTypeShort[shownValue]}
          // Filled while the value in use is the one on display.
          variant={shownValue === activeValue ? 'filled' : 'outlined'}
          onClick={hasMenu ? (event) => setAnchorEl(event.currentTarget) : undefined}
          clickable={hasMenu}
          size="small"
        />
      </Tooltip>
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
        slotProps={{ paper: { sx: { minWidth: 160 } } }}
      >
        {availableDisplayTypes.map((type) => (
          <MenuItem
            key={type}
            dense
            selected={type === shownValue}
            onClick={() => {
              setValueToDisplay(type)
              setAnchorEl(null)
            }}
          >
            <ListItemIcon>
              <ValueSymbol type={type} filled={type === activeValue} />
            </ListItemIcon>
            <ListItemText slotProps={{ primary: { variant: 'body2' } }}>
              {displayTypeLabels[type]}
            </ListItemText>
          </MenuItem>
        ))}
        {refusable.length > 0 && <Divider />}
        {refusable.map(({ source, label }) => (
          <MenuItem key={source} dense onClick={() => toggleRejected(source)}>
            <ListItemIcon>
              {isRejected(attribute, source) ? (
                <UndoIcon fontSize="small" />
              ) : (
                <BlockIcon fontSize="small" />
              )}
            </ListItemIcon>
            <ListItemText slotProps={{ primary: { variant: 'body2' } }}>
              {isRejected(attribute, source) ? `Use ${label}` : `Reject ${label}`}
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
            <ListItemText slotProps={{ primary: { variant: 'body2' } }}>
              Clear edit
            </ListItemText>
          </MenuItem>
        )}
      </Menu>
    </React.Fragment>
  )
}

/** Filled marks the value the item resolves to, the rest are outlined. */
function ValueSymbol({
  type,
  filled,
}: {
  type: ValueDisplayType
  filled: boolean
}): React.ReactElement {
  return (
    <Avatar
      sx={{
        width: 20,
        height: 20,
        fontSize: '0.7rem',
        bgcolor: filled ? 'primary.main' : 'transparent',
        color: filled ? 'primary.contrastText' : 'text.secondary',
        border: filled ? undefined : '1px solid',
        borderColor: 'divider',
      }}
    >
      {displayTypeShort[type]}
    </Avatar>
  )
}
