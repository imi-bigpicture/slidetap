import React, { useEffect, useState, type ReactElement } from 'react'
import type { Project } from 'models/project'

import projectApi from 'services/api/project_api'
import Tabs from '@mui/material/Tabs'
import Tab from '@mui/material/Tab'
import Badge from '@mui/material/Badge'
import StepHeader from 'components/step_header'
import { Button, Card, CardContent } from '@mui/material'
import { AttributeTable } from 'components/table'
import { type ItemTableItem, Action } from 'models/table_item'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import itemApi from 'services/api/item_api'
import ItemDetails from 'components/item/item_details'
import { ItemType } from 'models/schema'
import { ArrowBack, Recycling } from '@mui/icons-material'

interface CurateProps {
  project: Project
  showImages: boolean
}

export default function Curate({ project, showImages }: CurateProps): ReactElement {
  const [displayRecycled, setDisplayRecycled] = useState(false)
  const [loading, setLoading] = useState<boolean>(true)
  const [items, setItems] = useState<ItemTableItem[]>([])
  const [tabValue, setTabValue] = useState(0)
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(false)
  const [itemDetailUid, setItemDetaulUid] = React.useState<string>()
  const [itemDetailAction, setItemDetailAction] = React.useState<Action>(Action.VIEW)

  useEffect(() => {
    const getItems = (): void => {
      projectApi
        .getItems(
          project.uid,
          project.items[tabValue].schema.uid,
          !displayRecycled,
          displayRecycled,
        )
        .then((items) => {
          setItems(items)
          setLoading(false)
        })
        .catch((x) => {
          console.error('Failed to get items', x)
        })
    }
    getItems()
    // const intervalId = setInterval(() => {
    //     getItems()
    // }, 10000)
    // return () => clearInterval(intervalId)
  }, [tabValue, project, displayRecycled])

  const handleTabChange = (event: React.SyntheticEvent, newValue: number): void => {
    setLoading(true)
    setTabValue(newValue)
  }

  const handleItemAction = (itemUid: string, action: Action): void => {
    console.log('handleItemAction', itemUid, action)
    if (action === Action.DELETE || action === Action.RESTORE) {
      itemApi.select(itemUid, action === Action.RESTORE).catch((x) => {
        console.error('Failed to select item', x)
      })
      return
    }
    setItemDetaulUid(itemUid)
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
        <Button
          onClick={() => {
            setDisplayRecycled(!displayRecycled)
          }}
          variant="contained"
        >
          {displayRecycled ? <ArrowBack /> : <Recycling />}
        </Button>
      </Grid>
      <Grid xs>
        <Card>
          <CardContent>
            <Tabs value={tabValue} onChange={handleTabChange}>
              {project.items
                .filter(
                  (item) => item.schema.itemValueType !== ItemType.IMAGE || showImages,
                )
                .map((item, index) => (
                  <Tab
                    key={index}
                    label={
                      <Badge badgeContent={item.count} color="primary" max={99999}>
                        {item.schema.name}
                      </Badge>
                    }
                  />
                ))}
            </Tabs>
            <AttributeTable
              columns={[
                { id: 'name', header: 'Id', accessorKey: 'name' },
                ...project.items[tabValue].schema.attributes
                  .filter((attribute) => attribute.displayInTable)
                  .map((attribute) => {
                    return {
                      header: attribute.displayName,
                      accessorKey: `attributes.${attribute.tag}.displayValue`,
                      id: `attributes.${attribute.tag}`,
                    }
                  }),
              ]}
              data={items
                .filter((item) => !displayRecycled === item.selected)
                .map((item) => {
                  return {
                    uid: item.uid,
                    name: item.name,
                    selected: item.selected,
                    attributes: item.attributes,
                  }
                })}
              rowsSelectable={true}
              isLoading={loading}
              displayRecycled={displayRecycled}
              onRowAction={handleItemAction}
              onRowsStateChange={handleStateChange}
              onRowsEdit={(itemUids: string[]): void => {
                console.log('edit multiple', itemUids)
              }} // TODO
              onNew={(): void => {
                console.log('add new', project.items[tabValue].schema)
              }} // TODO
            />
          </CardContent>
        </Card>
      </Grid>
      {itemDetailsOpen && (
        <Grid xs={3}>
          <ItemDetails
            itemUid={itemDetailUid}
            action={itemDetailAction}
            setOpen={setItemDetailsOpen}
          />
        </Grid>
      )}
    </Grid>
  )
}
