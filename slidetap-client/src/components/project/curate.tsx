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

import type { Project } from 'models/project'
import React, { useState, type ReactElement } from 'react'

import { Badge, Stack, Tab, Tabs, styled, type BadgeProps } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import DisplayItemDetails from 'components/item/item_details'
import StepHeader from 'components/step_header'
import { AttributeTable } from 'components/table'
import { Action } from 'models/action'
import { ItemType, type ItemSchema } from 'models/schema'
import type { ColumnFilter, ColumnSort, Item } from 'models/table_item'
import itemApi from 'services/api/item_api'

interface CurateProps {
  project: Project
  showImages: boolean
}

const TabBadge = styled(Badge)<BadgeProps>(({ theme }) => ({
  '& .MuiBadge-badge': {
    right: -5,
    top: -5,
    border: `2px solid ${theme.palette.background.paper}`,
    padding: '0 4px',
  },
}))

export default function Curate({ project, showImages }: CurateProps): ReactElement {
  const [schema, setSchema] = useState<ItemSchema>(project.items[0].schema)
  const [tabValue, setTabValue] = useState(0)
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(false)
  const [itemDetailUid, setItemDetailUid] = React.useState<string>()
  const [itemDetailAction, setItemDetailAction] = React.useState<
    Action.VIEW | Action.EDIT | Action.NEW | Action.COPY
  >(Action.VIEW)
  const getItems = async (
    schema: ItemSchema,
    start: number,
    size: number,
    filters: ColumnFilter[],
    sorting: ColumnSort[],
    recycled?: boolean,
    invalid?: boolean,
  ): Promise<{ items: Item[]; count: number }> => {
    const request = {
      start,
      size,
      identifierFilter: filters.find((filter) => filter.id === 'id')?.value as string,
      attributeFilters:
        filters.length > 0
          ? filters
              .filter((filter) => filter.id.startsWith('attributes.'))
              .reduce<Record<string, string>>(
                (attributeFilters, filter) => ({
                  ...attributeFilters,
                  [filter.id.split('attributes.')[1]]: String(filter.value),
                }),
                {},
              )
          : undefined,
      sorting: sorting.length > 0 ? sorting : undefined,
      included: recycled !== undefined ? !recycled : undefined,
      valid: invalid !== undefined ? !invalid : undefined,
    }
    return await itemApi.getItems<Item>(schema.uid, project.uid, request)
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number): void => {
    setTabValue(newValue)
    setSchema(project.items[newValue].schema)
  }

  const handleItemAction = (itemUid: string, action: Action): void => {
    if (action === Action.DELETE || action === Action.RESTORE) {
      itemApi.select(itemUid, action === Action.RESTORE).catch((x) => {
        console.error('Failed to select item', x)
      })
      return
    }
    setItemDetailUid(itemUid)
    setItemDetailAction(action)
    setItemDetailsOpen(true)
  }

  const handleStateChange = (itemUids: string[], state: boolean): void => {
    itemUids.forEach((itemUid) => {
      itemApi.select(itemUid, state).catch((x) => {
        console.error('Failed to select item', x)
      })
    })
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid xs={12}>
        <StepHeader title="Curation" description="Curate items in project" />
      </Grid>
      <Grid xs={12}>
        <Stack direction="row" spacing={2}></Stack>
      </Grid>
      <Grid xs>
        <Tabs value={tabValue} onChange={handleTabChange}>
          {project.items.map((item, index) => (
            <Tab
              key={index}
              disabled={item.schema.itemValueType === ItemType.IMAGE && !showImages}
              label={
                <TabBadge badgeContent={item.count} color="primary" max={99999}>
                  {item.schema.displayName}
                </TabBadge>
              }
            />
          ))}
        </Tabs>
        <AttributeTable
          getItems={getItems}
          schema={schema}
          rowsSelectable={true}
          onRowAction={handleItemAction}
          onRowsStateChange={handleStateChange}
          onRowsEdit={(itemUids: string[]): void => {
            console.log('edit multiple', itemUids)
          }} // TODO
          onNew={(): void => {
            setItemDetailUid('')
            setItemDetailAction(Action.NEW)
            setItemDetailsOpen(true)
          }}
        />
      </Grid>
      {itemDetailsOpen && (
        <Grid xs={4}>
          <DisplayItemDetails
            itemUid={itemDetailUid}
            itemSchemaUid={schema.uid}
            projectUid={project.uid}
            action={itemDetailAction}
            setOpen={setItemDetailsOpen}
          />
        </Grid>
      )}
    </Grid>
  )
}
