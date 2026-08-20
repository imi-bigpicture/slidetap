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

import { ListItemIcon } from '@mui/material'
import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Drawer from '@mui/material/Drawer'
import ListItem from '@mui/material/ListItem'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Toolbar from '@mui/material/Toolbar'
import React, { type ReactElement } from 'react'
import { Link as RouterLink, Routes } from 'react-router-dom'

const drawerWidth = 160

export interface MenuItem {
  name: string
  icon: React.ReactNode
  /** What the entry stands for, and what marks it as the one being shown. */
  path: string
  /** Where it actually goes, when that is not the path itself — the view as it
   * was last left, tab and filters included. */
  to?: string
  enabled?: boolean
  description?: string
}

export interface MenuSection {
  title: string
  name: string
  description?: string
  items: MenuItem[]
}

interface SideBarProps {
  sections: MenuSection[]
  routes: React.ReactElement[]
  selectedView: string
  /** What an item's `path` hangs under, so each entry can be a real link. */
  basePath: string
}

interface DrawerSectionProps {
  section: MenuSection
  basePath: string
  view: string
}

interface DrawerSectionTitleProps {
  section: MenuSection
}

interface DrawerSectionItemProps {
  item: MenuItem
  basePath: string
  view: string
}

function DrawerSectionTitle({ section }: DrawerSectionTitleProps): ReactElement {
  return (
    <ListItem disablePadding>
      <ListItemButton alignItems="flex-start">
        <ListItemText
          primary={section.title}
          secondary={
            <React.Fragment>
              <span style={{ display: 'block', fontWeight: 500 }}>{section.name}</span>
              {section.description && (
                <span style={{ display: 'block', fontSize: 12 }}>
                  {section.description}
                </span>
              )}
            </React.Fragment>
          }
          slotProps={{
            primary: {
              sx: {
                fontWeight: 'bold',
                lineHeight: '20px',
                mb: '2px',
              },
            },
            secondary: {
              component: 'div',
              noWrap: false,
            },
          }}
        />
      </ListItemButton>
    </ListItem>
  )
}

function DrawerSectionItem({
  item,
  basePath,
  view,
}: DrawerSectionItemProps): ReactElement {
  return (
    <ListItem key={item.name} disablePadding sx={{}}>
      {/* A link rather than a button: a click goes there as before, and the
          browser keeps its own middle-click, ctrl-click and "open in new
          window" for a view someone wants beside the one they are on. */}
      <ListItemButton
        component={RouterLink}
        to={`${basePath}/${item.to ?? item.path}`}
        selected={view === item.path}
        disabled={item.enabled !== undefined && !item.enabled}
        sx={{ py: 0, px: 2, minHeight: 32, gap: 0 }}
        title={item.description}
      >
        <ListItemIcon sx={{ color: 'inherit', minWidth: 32, mr: 1 }}>
          {item.icon}
        </ListItemIcon>
        <ListItemText
          primary={item.name}
          slotProps={{
            primary: { sx: { fontSize: 14, fontWeight: 'medium' } },
          }}
        />
      </ListItemButton>
    </ListItem>
  )
}

function DrawerSection({ section, basePath, view }: DrawerSectionProps): ReactElement {
  return (
    <React.Fragment>
      <DrawerSectionTitle section={section} />
      {section.items.map((item) => (
        <DrawerSectionItem
          key={item.name}
          item={item}
          basePath={basePath}
          view={view}
        />
      ))}
      <Divider />
    </React.Fragment>
  )
}

export default function SideBar({
  sections,
  routes,
  selectedView,
  basePath,
}: SideBarProps): ReactElement {
  return (
    <Box sx={{ display: 'flex' }}>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': { width: drawerWidth, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          {sections.map((section) => (
            <DrawerSection
              // Keyed by what the section is, not by what it currently names:
              // stepping to another item changes the name, and keying on that
              // would throw away the whole section and build it again.
              key={section.title}
              section={section}
              basePath={basePath}
              view={selectedView}
            />
          ))}
        </Box>
      </Drawer>
      {/* Bounded by the window rather than by what is on the page: without
          this a wide page — a strip of thumbnails, a broad table — widens the
          whole app and takes the sidebar with it. */}
      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: 1 }}>
        <Routes>{routes}</Routes>
      </Box>
    </Box>
  )
}
