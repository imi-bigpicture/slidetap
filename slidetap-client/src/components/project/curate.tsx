import type { Project } from 'models/project'
import React, { useState, type ReactElement } from 'react'

import { Badge, Card, CardContent, Stack, Tab, Tabs } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import DisplayItemDetails from 'components/item/item_details'
import StepHeader from 'components/step_header'
import { AttributeTable } from 'components/table'
import { Action } from 'models/action'
import { ItemType, type ItemSchema } from 'models/schema'
import type { Item } from 'models/table_item'
import itemApi from 'services/api/item_api'

interface CurateProps {
  project: Project
  showImages: boolean
}

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
    recycled?: boolean,
    invalid?: boolean,
  ): Promise<{ items: Item[]; count: number }> => {
    return await itemApi.getItems<Item>(
      schema.uid,
      project.uid,
      start,
      size,
      recycled,
      invalid,
    )
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
    <Grid container spacing={2}>
      <Grid xs={12}>
        <StepHeader title="Curation" description="Curate items in project" />
      </Grid>
      <Grid xs={12}>
        <Stack direction="row" spacing={2}></Stack>
      </Grid>
      <Grid xs>
        <Card>
          <CardContent>
            <Tabs value={tabValue} onChange={handleTabChange}>
              {project.items.map((item, index) => (
                <Tab
                  key={index}
                  disabled={item.schema.itemValueType === ItemType.IMAGE && !showImages}
                  label={
                    <Badge badgeContent={item.count} color="primary" max={99999}>
                      {item.schema.name}
                    </Badge>
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
          </CardContent>
        </Card>
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
