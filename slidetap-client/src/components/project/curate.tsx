import type { Project } from 'models/project'
import React, { useEffect, useState, type ReactElement } from 'react'

import { PriorityHigh, Recycling, Warning } from '@mui/icons-material'
import {
  Badge,
  Card,
  CardContent,
  IconButton,
  Stack,
  Tab,
  Tabs,
  Tooltip,
} from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import DisplayItemDetails from 'components/item/item_details'
import StepHeader from 'components/step_header'
import { AttributeTable } from 'components/table'
import { Action } from 'models/action'
import { ItemType } from 'models/schema'
import type { Item } from 'models/table_item'
import itemApi from 'services/api/item_api'

interface CurateProps {
  project: Project
  showImages: boolean
}

export default function Curate({ project, showImages }: CurateProps): ReactElement {
  const [displayRecycled, setDisplayRecycled] = useState(false)
  const [displayOnlyInValid, setDisplayOnlyInValid] = useState(false)
  const [loading, setLoading] = useState<boolean>(true)
  const [items, setItems] = useState<Item[]>([])
  const [tabValue, setTabValue] = useState(0)
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(false)
  const [itemDetailUid, setItemDetailUid] = React.useState<string>()
  const [itemDetailAction, setItemDetailAction] = React.useState<
    Action.VIEW | Action.EDIT | Action.NEW | Action.COPY
  >(Action.VIEW)

  useEffect(() => {
    const getItems = (): void => {
      itemApi
        .getItems<Item>(
          project.uid,
          project.items[tabValue].schema.uid,
          !displayRecycled,
          displayOnlyInValid ? false : undefined,
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
  }, [tabValue, project, displayRecycled, displayOnlyInValid])

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
        <Stack direction="row" spacing={2}>
          <Tooltip title="Toggle display of deleted items">
            <IconButton
              onClick={() => {
                setDisplayOnlyInValid(false)
                setDisplayRecycled(!displayRecycled)
              }}
              color={displayRecycled ? 'primary' : 'default'}
            >
              <Recycling />
            </IconButton>
          </Tooltip>
          <Tooltip title="Toggle display of invalid items">
            <IconButton
              onClick={() => {
                setDisplayRecycled(false)
                setDisplayOnlyInValid(!displayOnlyInValid)
              }}
              color={displayOnlyInValid ? 'primary' : 'default'}
            >
              <Warning />
            </IconButton>
          </Tooltip>
        </Stack>
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
                { id: 'id', header: 'Id', accessorKey: 'identifier' },
                {
                  id: 'valid',
                  header: 'Valid',
                  accessorKey: 'valid',
                  Cell: ({ cell }) =>
                    cell.getValue<boolean>() ? <></> : <PriorityHigh color="warning" />,
                },
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
              data={items.map((item) => {
                console.log(item)
                return {
                  uid: item.uid,
                  identifier: item.identifier,
                  selected: item.selected,
                  valid: item.valid,
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
          <DisplayItemDetails
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
