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

import React, { Fragment } from 'react'

import MoreVertIcon from '@mui/icons-material/MoreVert'
import { Divider, IconButton, Menu, MenuItem } from '@mui/material'
import { ItemDetailAction } from 'src/models/action'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import { ValueDisplayType } from 'src/models/value_display_type'

interface ValueMenuProps {
  attribute: Attribute<AttributeValueTypes>
  action: ItemDetailAction
  valueToDisplay: ValueDisplayType
  setValueToDisplay: (value: ValueDisplayType) => void
  handleAttributeUpdate: (attribute: Attribute<AttributeValueTypes>) => void
}

export default function ValueMenu({
  attribute,
  action,
  valueToDisplay,
  setValueToDisplay,
  handleAttributeUpdate,
}: ValueMenuProps): React.ReactElement {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null)
  const open = Boolean(anchorEl)
  const handleClick = (event: React.MouseEvent<HTMLButtonElement>): void => {
    setAnchorEl(event.currentTarget)
  }
  const handleClose = (): void => {
    setAnchorEl(null)
  }
  const handleViewCurrentValue = (): void => {
    setValueToDisplay(ValueDisplayType.CURRENT)
    handleClose()
  }
  const handleViewOriginalValue = (): void => {
    setValueToDisplay(ValueDisplayType.ORIGINAL)
    handleClose()
  }
  const handleViewUpdatedValue = (): void => {
    setValueToDisplay(ValueDisplayType.UPDATED)
    handleClose()
  }
  const handleViewMapping = (): void => {
    setValueToDisplay(ValueDisplayType.MAPPED)
    handleClose()
  }
  const handleReset = (): void => {
    attribute.updatedValue = null
    handleAttributeUpdate(attribute)
    handleClose()
  }
  const handleClear = (): void => {
    attribute.updatedValue = null
    handleAttributeUpdate(attribute)
    handleClose()
  }
  return (
    <Fragment>
      <IconButton
        aria-label="more"
        id="long-button"
        aria-controls={open ? 'long-menu' : undefined}
        aria-expanded={open ? 'true' : undefined}
        aria-haspopup="true"
        onClick={handleClick}
      >
        <MoreVertIcon />
      </IconButton>
      <Menu
        id="basic-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          'aria-labelledby': 'basic-button',
        }}
      >
        <MenuItem
          onClick={handleViewCurrentValue}
          disabled={valueToDisplay === ValueDisplayType.CURRENT}
        >
          Current value
        </MenuItem>
        <MenuItem
          onClick={handleViewUpdatedValue}
          disabled={valueToDisplay === ValueDisplayType.UPDATED}
        >
          Updated value
        </MenuItem>
        <MenuItem
          onClick={handleViewOriginalValue}
          disabled={
            valueToDisplay === ValueDisplayType.ORIGINAL ||
            attribute.originalValue === undefined
          }
        >
          Original value
        </MenuItem>
        <MenuItem
          onClick={handleViewMapping}
          disabled={valueToDisplay === ValueDisplayType.MAPPED}
        >
          Mapping
        </MenuItem>
        <Divider />
        <MenuItem onClick={handleClear} disabled={action !== ItemDetailAction.EDIT}>
          Clear
        </MenuItem>
        <MenuItem onClick={handleReset} disabled={action !== ItemDetailAction.EDIT}>
          Reset
        </MenuItem>
        <MenuItem onClick={handleClose}>Copy</MenuItem>
      </Menu>
    </Fragment>
  )
}
