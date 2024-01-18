import type { Project } from 'models/project'
import React, { useEffect, useState, type ReactElement } from 'react'

import { ArrowBack, Recycling } from '@mui/icons-material'
import { Button, Card, CardContent } from '@mui/material'
import Badge from '@mui/material/Badge'
import Tab from '@mui/material/Tab'
import Tabs from '@mui/material/Tabs'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import ItemDetails from 'components/item/item_details'
import StepHeader from 'components/step_header'
import { AttributeTable } from 'components/table'
import { ItemType } from 'models/schema'
import { Action, type ItemTableItem } from 'models/table_item'
import itemApi from 'services/api/item_api'
import projectApi from 'services/api/project_api'

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
  const [itemDetailUid, setItemDetailUid] = React.useState<string>()
  const [itemDetailAction, setItemDetailAction] = React.useState<
    Action.VIEW | Action.EDIT | Action.NEW | Action.COPY
  >(Action.VIEW)

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
          <ItemDetails
            itemUid={itemDetailUid}
            itemSchemaUid={project.items[tabValue].schema.uid}
            projectUid={project.uid}
            action={itemDetailAction}
            setOpen={setItemDetailsOpen}
          />
        </Grid>
      )}
    </Grid>
  )
}
