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

import Box from '@mui/material/Box'
import Divider from '@mui/material/Divider'
import Drawer from '@mui/material/Drawer'
import List from '@mui/material/List'
import ListItem from '@mui/material/ListItem'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import Toolbar from '@mui/material/Toolbar'
import React, { Fragment, type ReactElement } from 'react'
import { Routes } from 'react-router-dom'

const drawerWidth = 160

export interface MenuItem {
  name: string
  path: string
  enabled?: boolean
  hidden?: boolean
}

export interface MenuSection {
  name: string
  description?: string
  path?: string
  items?: MenuItem[]
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

function DrawerSectionTitle({
  section,
  handleViewChange,
  view,
}: DrawerSectionProps): ReactElement {
  if (section.path !== undefined) {
    return (
      <ListItem>
        <ListItemButton
          id={section.path}
          onClick={handleViewChange}
          selected={view === section.path}
        >
          <ListItemText
            primaryTypographyProps={{ fontWeight: 'bold' }}
            primary={section.name}
            secondary={section.description}
          />
        </ListItemButton>
      </ListItem>
    )
  } else {
    return (
      <Fragment>
        <ListItem>
          <ListItemText
            primaryTypographyProps={{ fontWeight: 'bold' }}
            primary={section.name}
            secondary={section.description}
          />
        </ListItem>
      </Fragment>
    )
  }
}

function DrawerSectionItems({
  section,
  handleViewChange,
  view,
}: DrawerSectionProps): ReactElement {
  return (
    <List>
      {section.items
        ?.filter((item) => item.hidden === undefined || !item.hidden)
        .map((item) => (
          <ListItem key={item.name} disablePadding>
            <ListItemButton
              id={item.path}
              onClick={handleViewChange}
              selected={view === item.path}
              disabled={item.enabled !== undefined && !item.enabled}
            >
              <ListItemText primary={item.name} />
            </ListItemButton>
          </ListItem>
        ))}
    </List>
  )
}

function DrawerSection({
  section,
  handleViewChange,
  view,
}: DrawerSectionProps): ReactElement {
  return (
    <React.Fragment>
      <DrawerSectionTitle
        section={section}
        handleViewChange={handleViewChange}
        view={view}
      />
      <DrawerSectionItems
        section={section}
        handleViewChange={handleViewChange}
        view={view}
      />
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
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Routes>{routes.map((item) => item)}</Routes>
      </Box>
    </Box>
  )
}
