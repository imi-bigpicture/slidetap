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

import { Badge, Tab, Tabs, styled, type BadgeProps } from '@mui/material'
import Grid from '@mui/material/Grid2'
import React, { useState, type ReactElement } from 'react'
import type { Project } from 'src/models/project'

import DisplayItemDetails from 'src/components/item/item_details'
import { ItemTable } from 'src/components/table/item_table'
import { Action } from 'src/models/action'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import { Item } from 'src/models/item'
import { ItemSchema } from 'src/models/schema/item_schema'
import type { ColumnFilter, ColumnSort } from 'src/models/table_item'
import itemApi from 'src/services/api/item_api'

interface CurateProps {
  project: Project
  batch?: Batch
  itemSchemas: ItemSchema[]
}

const TabBadge = styled(Badge)<BadgeProps>(({ theme }) => ({
  '& .MuiBadge-badge': {
    right: -5,
    top: -5,
    border: `2px solid ${theme.palette.background.paper}`,
    padding: '0 4px',
  },
}))

export default function Curate({
  project,
  batch,
  itemSchemas,
}: CurateProps): ReactElement {
  const [schema, setSchema] = useState<ItemSchema>(itemSchemas[0])
  const [tabValue, setTabValue] = useState(0)
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(false)
  const [itemDetailUid, setItemDetailUid] = React.useState<string>()
  const [itemDetailAction, setItemDetailAction] = React.useState<
    Action.VIEW | Action.EDIT | Action.NEW | Action.COPY
  >(Action.VIEW)
  const getItems = async (
    schemaUid: string,
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
    return await itemApi.getItems<Item>(
      schemaUid,
      project.datasetUid,
      batch?.uid,
      request,
    )
  }

  const handleTabChange = (_: React.SyntheticEvent, newValue: number): void => {
    setTabValue(newValue)
    setSchema(itemSchemas[newValue])
  }

  const handleItemView = (item: Item): void => {
    setItemDetailUid(item.uid)
    setItemDetailAction(Action.VIEW)
    setItemDetailsOpen(true)
  }

  const handleItemEdit = (item: Item): void => {
    setItemDetailUid(item.uid)
    setItemDetailAction(Action.EDIT)
    setItemDetailsOpen(true)
  }

  const handleItemDeleteOrRestore = (item: Item): void => {
    itemApi.select(item.uid, true).catch((x) => {
      console.error('Failed to select item', x)
    })
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
      <Grid size={{ xs: itemDetailsOpen ? 8 : 12 }}>
        <Tabs value={tabValue} onChange={handleTabChange}>
          {itemSchemas.map((schema, index) => (
            <Tab
              key={index}
              label={
                <TabBadge badgeContent={0} color="primary" max={99999}>
                  {schema.displayName}
                </TabBadge>
              }
            />
          ))}
        </Tabs>
        <ItemTable
          getItems={getItems}
          schema={schema}
          rowsSelectable={true}
          actions={[
            { action: Action.VIEW, onAction: handleItemView },
            { action: Action.EDIT, onAction: handleItemEdit },
            {
              action: Action.DELETE,
              onAction: handleItemDeleteOrRestore,
            },
            {
              action: Action.RESTORE,
              onAction: handleItemDeleteOrRestore,
            },
            {
              action: Action.IMAGES,
              onAction: (item: Item): void => {
                window.open(
                  `/project/${project.uid}/images_for_item/${item.uid}`,
                  '_blank',
                  'noopener,noreferrer,width=1024,height=1024',
                )
              },
              enabled: (): boolean => {
                return (
                  batch != undefined &&
                  batch?.status >= BatchStatus.IMAGE_PRE_PROCESSING
                )
              },
            },
          ]}
          onRowsStateChange={handleStateChange}
          onRowsEdit={(): void => {}} // TODO
          onNew={(): void => {
            setItemDetailUid('')
            setItemDetailAction(Action.NEW)
            setItemDetailsOpen(true)
          }}
          refresh={batch?.status === BatchStatus.METADATA_SEARCHING}
        />
      </Grid>
      {itemDetailsOpen && (
        <Grid size={{ xs: 4 }}>
          <DisplayItemDetails
            itemUid={itemDetailUid}
            itemSchemaUid={schema.uid}
            projectUid={project.uid}
            action={itemDetailAction}
            setOpen={setItemDetailsOpen}
            setItemUid={setItemDetailUid}
            setItemAction={setItemDetailAction}
          />
        </Grid>
      )}
    </Grid>
  )
}
