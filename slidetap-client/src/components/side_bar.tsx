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
import { Routes } from 'react-router-dom'

const drawerWidth = 160

export interface MenuItem {
  name: string
  icon: React.ReactNode
  path: string
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
  changeView: (to: string) => void
}

interface DrawerSectionProps {
  section: MenuSection
  handleViewChange: (event: React.MouseEvent<HTMLElement>) => void
  view: string
}

interface DrawerSectionTitleProps {
  section: MenuSection
}

interface DrawerSectionItemProps {
  item: MenuItem
  handleViewChange: (event: React.MouseEvent<HTMLElement>) => void
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
              fontWeight: 'bold',
              lineHeight: '20px',
              mb: '2px',
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
  handleViewChange,
  view,
}: DrawerSectionItemProps): ReactElement {
  return (
    <ListItem key={item.name} disablePadding sx={{}}>
      <ListItemButton
        id={item.path}
        onClick={handleViewChange}
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
            primary: { fontSize: 14, fontWeight: 'medium' },
          }}
        />
      </ListItemButton>
    </ListItem>
  )
}

function DrawerSection({
  section,
  handleViewChange,
  view,
}: DrawerSectionProps): ReactElement {
  return (
    <React.Fragment>
      <DrawerSectionTitle section={section} />
      {section.items.map((item) => (
        <DrawerSectionItem
          key={item.name}
          item={item}
          handleViewChange={handleViewChange}
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
  changeView,
}: SideBarProps): ReactElement {
  function handleViewChange(event: React.MouseEvent<HTMLElement>): void {
    const newView = event.currentTarget.id
    changeView(newView)
  }
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
              key={section.name}
              section={section}
              handleViewChange={handleViewChange}
              view={selectedView}
            />
          ))}
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 1 }}>
        <Routes>{routes}</Routes>
      </Box>
    </Box>
  )
}
