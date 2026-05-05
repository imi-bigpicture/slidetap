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
  Box,
  Button,
  FormControl,
  Paper,
  Popover,
  Stack,
  Tab,
  TextField,
} from '@mui/material'
import React, { useCallback, useEffect, useRef, useState, type ReactElement } from 'react'
import { useSearchParams } from 'react-router-dom'
import type { Project } from 'src/models/project'

import { Cancel, Delete, RestoreFromTrash } from '@mui/icons-material'
import { TabContext, TabList, TabPanel } from '@mui/lab'
import DisplayItemDetails from 'src/components/item/item_details'
import { ItemTable } from 'src/components/table/item_table'
import { useError } from 'src/contexts/error/error_context'
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
  const { showError } = useError()
  const [searchParams, setSearchParams] = useSearchParams()
  const [tabValue, setTabValue] = useState(itemSchemas[0].uid)
  const [itemDetailsOpen, setItemDetailsOpen] = React.useState(false)
  const [itemDetailUid, setItemDetailUid] = React.useState<string>('')
  const [itemDetailAction, setItemDetailAction] = React.useState<ItemDetailAction>(
    ItemDetailAction.VIEW,
  )

  useEffect(() => {
    const openItem = searchParams.get('openItem')
    if (openItem) {
      setItemDetailUid(openItem)
      setItemDetailAction(ItemDetailAction.VIEW)
      setItemDetailsOpen(true)
      const next = new URLSearchParams(searchParams)
      next.delete('openItem')
      setSearchParams(next, { replace: true })
    }
  }, [searchParams, setSearchParams])
  const [privateOpen, setPrivateOpen] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const [itemSelectAnchorEl, setItemSelectAnchorEl] = useState<HTMLElement | null>(null)
  const [openedItemSelectUids, setOpenedItemSelectUids] = useState<string[]>([])
  const [openedItemSelect, setOpenedItemSelect] = useState<ItemSelect | null>(null)
  const itemSelectOpen = Boolean(itemSelectAnchorEl)
  const [newTagsToSave, setNewTagsToSave] = useState<string[]>([])
  const [currentItemUids, setCurrentItemUids] = useState<string[]>([])
  const [panelWidth, setPanelWidth] = useState(500)
  const isResizing = useRef(false)

  const handleResizeStart = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault()
      isResizing.current = true
      const startX = event.clientX
      const startWidth = panelWidth

      const handleMouseMove = (e: MouseEvent) => {
        if (!isResizing.current) return
        const newWidth = startWidth - (e.clientX - startX)
        setPanelWidth(Math.max(300, Math.min(newWidth, window.innerWidth - 300)))
      }

      const handleMouseUp = () => {
        isResizing.current = false
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }

      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    },
    [panelWidth],
  )

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

  const handleRowsRemap = (itemUids: string[]): void => {
    itemUids.forEach((uid) => {
      itemApi.remap(uid).catch((error) => {
        showError(`Failed to remap item ${uid}`, error)
      })
    })
  }

  return (
    <React.Fragment>
      <Box sx={{
        display: 'grid',
        gridTemplateColumns: itemDetailsOpen && itemDetailUid !== '' ? `minmax(0, 1fr) ${panelWidth}px` : '1fr',
        width: '100%',
        overflow: 'hidden',
      }}>
        <Box sx={{ minWidth: 0, overflow: 'auto' }}>
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
                  onRowsRemap={handleRowsRemap}
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
                  onItemUidsChange={setCurrentItemUids}
                  refresh={batch?.status === BatchStatus.METADATA_SEARCHING}
                />
              </TabPanel>
            ))}
          </TabContext>
        </Box>
        {itemDetailsOpen && itemDetailUid !== '' && (
          <Box sx={{ display: 'flex', minWidth: 0, overflow: 'hidden' }}>
            <Box
              onMouseDown={handleResizeStart}
              sx={{
                width: 6,
                cursor: 'col-resize',
                flexShrink: 0,
                backgroundColor: 'divider',
                '&:hover': { backgroundColor: 'action.hover' },
                borderRadius: 1,
                mx: 0.5,
              }}
            />
            <Box sx={{ flexGrow: 1, minWidth: 0, overflow: 'auto' }}>
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
                itemUids={currentItemUids}
              />
            </Box>
          </Box>
        )}
      </Box>
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
                      showError('Failed to select item', error)
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
