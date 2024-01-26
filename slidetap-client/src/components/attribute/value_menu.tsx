import React, { Fragment } from 'react'

import MoreVertIcon from '@mui/icons-material/MoreVert'
import { Divider, IconButton, Menu, MenuItem } from '@mui/material'
import { Action } from 'models/action'
import { ValueDisplayType, type Attribute } from 'models/attribute'

interface ValueMenuProps {
  attribute: Attribute<any, any>
  action: Action
  valueToDisplay: ValueDisplayType
  setValueToDisplay: (value: ValueDisplayType) => void
  handleAttributeUpdate: (attribute: Attribute<any, any>) => void
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
  const handleViewOriginalValue = (): void => {
    setValueToDisplay(ValueDisplayType.ORIGINAL)
    handleClose()
  }
  const handleViewUpdatedValue = (): void => {
    setValueToDisplay(ValueDisplayType.CURRENT)
    handleClose()
  }
  const handleViewMapping = (): void => {
    setValueToDisplay(ValueDisplayType.MAPPED)
    handleClose()
  }
  const handleReset = (): void => {
    attribute.value = attribute.originalValue
    handleAttributeUpdate(attribute)
    handleClose()
  }
  const handleClear = (): void => {
    attribute.value = undefined
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
          onClick={handleViewUpdatedValue}
          disabled={valueToDisplay === ValueDisplayType.CURRENT}
        >
          Current value
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
        <MenuItem onClick={handleClear} disabled={action !== Action.EDIT}>
          Clear
        </MenuItem>
        <MenuItem onClick={handleReset} disabled={action !== Action.EDIT}>
          Reset
        </MenuItem>
        <MenuItem onClick={handleClose}>Copy</MenuItem>
      </Menu>
    </Fragment>
  )
}
