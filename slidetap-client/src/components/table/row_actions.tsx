import { MoreVert } from '@mui/icons-material'
import {
  Box,
  IconButton,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  MenuList,
} from '@mui/material'
import { MRT_Row } from 'material-react-table'
import React, { useState } from 'react'
import { Action, ActionStrings } from 'src/models/action'
import ActionsIcons from './action_icons'

interface RowActionsProps<T extends { uid: string }> {
  row: MRT_Row<T>
  actions?: {
    action: Action
    onAction: (item: T, element: HTMLElement) => void
    enabled?: (item: T) => boolean
    inMenu?: boolean
  }[]
  displayRestore?: boolean
}

export default function RowActions<T extends { uid: string }>({
  row,
  actions,
  displayRestore,
}: RowActionsProps<T>): React.ReactElement {
  const [actionMenuOpen, setActionMenuOpen] = useState(false)
  const [actionMenuAnchorEl, setActionMenuAnchorEl] = useState<null | HTMLElement>(null)
  if (!actions) {
    return <Box />
  }
  const filteredActions = actions.filter((action) => {
    if (action.enabled !== undefined && !action.enabled(row.original)) {
      return false
    }
    if (displayRestore === undefined) {
      return true
    }
    if (displayRestore) {
      return action.action !== Action.DELETE
    } else {
      return action.action !== Action.RESTORE
    }
  })
  const iconActions = filteredActions.filter(
    (action) => action.inMenu === undefined || !action.inMenu,
  )
  const menuActions = filteredActions.filter((action) => action.inMenu)
  return (
    <Box>
      {iconActions.map((action) => (
        <IconButton
          size={'small'}
          key={action.action}
          onClick={(event) => action.onAction(row.original, event.currentTarget)}
        >
          {ActionsIcons[action.action]}
        </IconButton>
      ))}
      {menuActions.length > 0 && (
        <React.Fragment>
          <Menu
            open={actionMenuOpen}
            onClose={() => {
              setActionMenuOpen(false)
              setActionMenuAnchorEl(null)
            }}
            anchorEl={actionMenuAnchorEl}
          >
            <MenuList>
              {menuActions.map((action) => (
                <MenuItem
                  key={action.action}
                  onClick={(event) => {
                    action.onAction(row.original, event.currentTarget)
                  }}
                >
                  <ListItemIcon>{ActionsIcons[action.action]}</ListItemIcon>
                  <ListItemText>{ActionStrings[action.action]}</ListItemText>
                </MenuItem>
              ))}
            </MenuList>
          </Menu>
          <IconButton
            onClick={(event) => {
              setActionMenuAnchorEl(event.currentTarget)
              setActionMenuOpen(true)
            }}
          >
            <MoreVert />
          </IconButton>
        </React.Fragment>
      )}
    </Box>
  )
}
