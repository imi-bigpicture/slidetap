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

import {
  Button,
  FormControl,
  Paper,
  Popover,
  Stack,
  Tab,
  TextField,
} from '@mui/material'
import Grid from '@mui/material/Grid'
import React, { useState, type ReactElement } from 'react'
import type { Project } from 'src/models/project'

import { Cancel, Delete, RestoreFromTrash } from '@mui/icons-material'
import { TabContext, TabList, TabPanel } from '@mui/lab'
import DisplayItemDetails from 'src/components/item/item_details'
import { ItemTable } from 'src/components/table/item_table'
import { Action, ItemDetailAction } from 'src/models/action'
import { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import { Item } from 'src/models/item'
import { ItemSelect } from 'src/models/item_select'
import { ItemSchema } from 'src/models/schema/item_schema'
import itemApi from 'src/services/api/item_api'
import DisplayItemTags from '../item/display_item_tags'

interface CurateProps {
  project: Project
  batch?: Batch
  itemSchemas: ItemSchema[]
}

export default function Curate({
  project,
  batch,
  itemSchemas,
}: CurateProps): ReactElement {
  const [tabValue, setTabValue] = useState(itemSchemas[0].uid)
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(false)
  const [itemDetailUid, setItemDetailUid] = React.useState<string>('')
  const [itemDetailAction, setItemDetailAction] = React.useState<ItemDetailAction>(
    ItemDetailAction.VIEW,
  )
  const [privateOpen, setPrivateOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [itemSelectAnchorEl, setItemSelectAnchorEl] = useState<HTMLElement | null>(null)
  const [openedItemSelectUids, setOpenedItemSelectUids] = useState<string[]>([])
  const [openedItemSelect, setOpenedItemSelect] = useState<ItemSelect | null>(null)
  const itemSelectOpen = Boolean(itemSelectAnchorEl)
  const [newTagsToSave, setNewTagsToSave] = useState<string[]>([])

  const handleSelectItemClose = () => {
    setItemSelectAnchorEl(null)
    setOpenedItemSelect(null)
    setOpenedItemSelectUids([])
  }

  const handleItemUidView = (itemUid: string): void => {
    setItemDetailUid(itemUid)
    setItemDetailAction(ItemDetailAction.VIEW)
    setItemDetailsOpen(true)
  }

  const handleItemView = (item: Item): void => {
    setItemDetailUid(item.uid)
    setItemDetailAction(ItemDetailAction.VIEW)
    setItemDetailsOpen(true)
  }

  const handleItemEdit = (item: Item): void => {
    setItemDetailUid(item.uid)
    setItemDetailAction(ItemDetailAction.EDIT)
    setItemDetailsOpen(true)
  }

  const handleItemDeleteOrRestore = (item: Item, element: HTMLElement): void => {
    setOpenedItemSelect({
      select: !item.selected,
      comment: item.comment,
      tags: item.tags,
      additiveTags: false,
    })
    setOpenedItemSelectUids([item.uid])
    setItemSelectAnchorEl(element)
  }

  const handleStateChange = (
    itemUids: string[],
    state: boolean,
    element: HTMLElement,
  ): void => {
    setOpenedItemSelect({
      select: state,
      comment: null,
      tags: [],
      additiveTags: true,
    })
    setOpenedItemSelectUids(itemUids)
    setItemSelectAnchorEl(element)
  }

  return (
    <React.Fragment>
      <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
        <Grid size="grow">
          <TabContext value={tabValue}>
            <TabList onChange={(_, newValue) => setTabValue(newValue)}>
              {itemSchemas.map((schema) => (
                <Tab key={schema.uid} value={schema.uid} label={schema.displayName} />
              ))}
            </TabList>
            {itemSchemas.map((schema) => (
              <TabPanel key={schema.uid} value={schema.uid} style={{ padding: 0 }}>
                <ItemTable
                  project={project}
                  batch={batch}
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
                          'noopener,noreferrer,width=1024,height=1024,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes',
                        )
                      },
                      enabled: (): boolean => {
                        return (
                          batch != undefined &&
                          batch?.status >= BatchStatus.IMAGE_PRE_PROCESSING
                        )
                      },
                    },
                    {
                      action: Action.WINDOW,
                      onAction: (item: Item): void => {
                        window.open(
                          `/project/${project.uid}/item/${item.uid}`,
                          '_blank',
                          'noopener,noreferrer,width=600,height=800,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes',
                        )
                      },
                    },
                  ]}
                  onRowsStateChange={handleStateChange}
                  onRowView={handleItemUidView}
                  onNew={
                    batch !== undefined
                      ? async (): Promise<void> => {
                          const newItem = await itemApi.create(
                            schema.uid,
                            project.uid,
                            batch?.uid,
                          )
                          setItemDetailUid(newItem.uid)
                          setItemDetailAction(ItemDetailAction.EDIT)
                          setItemDetailsOpen(true)
                        }
                      : undefined
                  }
                  refresh={batch?.status === BatchStatus.METADATA_SEARCHING}
                />
              </TabPanel>
            ))}
          </TabContext>
        </Grid>
        {itemDetailsOpen && itemDetailUid !== '' && (
          <Grid
            size={{
              sm: privateOpen || previewOpen ? 8 : 6,
              md: privateOpen || previewOpen ? 7 : 5,
              lg: privateOpen || previewOpen ? 6 : 4,
            }}
          >
            <DisplayItemDetails
              projectUid={project.uid}
              itemUid={itemDetailUid}
              action={itemDetailAction}
              privateOpen={privateOpen}
              previewOpen={previewOpen}
              setOpen={setItemDetailsOpen}
              setItemUid={setItemDetailUid}
              setItemAction={setItemDetailAction}
              setPrivateOpen={setPrivateOpen}
              setPreviewOpen={setPreviewOpen}
              windowed={false}
            />
          </Grid>
        )}
      </Grid>
      {openedItemSelect && (
        <Popover
          open={itemSelectOpen}
          anchorEl={itemSelectAnchorEl}
          onClose={handleSelectItemClose}
          anchorOrigin={{
            vertical: 'bottom',
            horizontal: 'center',
          }}
          transformOrigin={{
            vertical: -10,
            horizontal: 'center',
          }}
        >
          <Paper sx={{ p: 2 }} style={{ maxWidth: '300px' }}>
            <FormControl component="fieldset" variant="standard">
              <Stack spacing={1} direction="column">
                <TextField
                  label="Comment"
                  size="small"
                  value={openedItemSelect.comment}
                  onChange={(event) => {
                    setOpenedItemSelect(
                      openedItemSelect
                        ? { ...openedItemSelect, comment: event.target.value }
                        : null,
                    )
                  }}
                  fullWidth
                />
                <DisplayItemTags
                  tagUids={openedItemSelect.tags ? openedItemSelect.tags : []}
                  newTagNames={newTagsToSave}
                  editable={true}
                  handleTagsUpdate={(tags) => {
                    setOpenedItemSelect(
                      openedItemSelect ? { ...openedItemSelect, tags: tags } : null,
                    )
                  }}
                  setNewTags={setNewTagsToSave}
                />
              </Stack>
            </FormControl>

            <Stack direction="row" spacing={1} sx={{ mt: 2, justifyContent: 'center' }}>
              <Button
                onClick={() => {
                  openedItemSelectUids?.forEach((uid) => {
                    itemApi.select(uid, openedItemSelect).catch((error) => {
                      console.error('Failed to select item', error)
                    })
                  })

                  handleSelectItemClose()
                }}
              >
                {openedItemSelect.select ? <RestoreFromTrash /> : <Delete />}
              </Button>
              <Button onClick={handleSelectItemClose}>
                <Cancel />
              </Button>
            </Stack>
          </Paper>
        </Popover>
      )}
    </React.Fragment>
  )
}
