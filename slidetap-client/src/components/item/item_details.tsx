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
  AccountTree,
  ArrowBack,
  AutoFixHigh,
  ChevronLeft,
  ChevronRight,
  AutoFixNormal,
  Close,
  Delete,
  Flag,
  MoreVert,
  Notes,
  PhotoLibrary,
  Preview,
  RateReview,
  RestoreFromTrash,
  Save,
  Security,
  TableChart,
  Undo,
} from '@mui/icons-material'
import {
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  IconButton,
  LinearProgress,
  ListItemIcon,
  ListItemText,
  Menu,
  MenuItem,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useCallback, useEffect, useState, type ReactElement } from 'react'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import Thumbnail from 'src/components/project/validate/thumbnail'
import { ImageViewerDialog } from 'src/components/image/image_viewer_dialog'
import Spinner from 'src/components/spinner'
import { ItemDetailAction } from 'src/models/action'
import { ReviewStatus } from 'src/models/review_status'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import { isImageItem } from 'src/models/helpers'
import type { Image } from 'src/models/item'
import { Item } from 'src/models/item'
import { ItemValueType } from 'src/models/item_value_type'
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import { useError } from 'src/contexts/error/error_context'
import type { ItemSelect } from 'src/models/item_select'
import itemApi from 'src/services/api/item_api'
import tagApi from 'src/services/api/tag_api'
import { queryKeys } from 'src/services/query_keys'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import { isReviewUnit, isUnderReviewUnit } from '../../models/schema/root_schema'
import ReviewFlagPopover from './review_flag_popover'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import AttributeDetails from '../attribute/attribute_details'
import NestedAttributeDetails from '../attribute/nested_attribute_details'
import ChipDivider from './chip_divider'
import DisplayItemTags from './display_item_tags'
import DisplayPreview from './display_preview'
import ItemViewHeader from './item_view_header'
import type { ItemStepping } from './use_item_stepping'
import DisplayItemIdentifiers from './item_identifiers'
import ItemSelectPopover from './item_select_popover'
import ItemLinkage from './linkage/item_linkage'

/** One entry in the strip of actions under the item. */
interface ItemAction {
  key: string
  icon: ReactElement
  label: string
  // The event is absent when the action is picked from the overflow menu,
  // where the menu item is gone by the time it is needed as an anchor.
  onClick?: (event?: React.MouseEvent<HTMLElement>) => void
  /** Where the action goes, for one that opens a view of the item: a link, so
   * the browser keeps its own ways of opening it. */
  href?: string
  disabled?: boolean
}

interface DisplayItemDetailsProps {
  projectUid: string
  itemUid: string
  action: ItemDetailAction
  privateOpen: boolean
  previewOpen: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  setItemUid: React.Dispatch<React.SetStateAction<string>>
  setItemAction: React.Dispatch<React.SetStateAction<ItemDetailAction>>
  setPrivateOpen: React.Dispatch<React.SetStateAction<boolean>>
  setPreviewOpen: React.Dispatch<React.SetStateAction<boolean>>
  windowed: boolean
  /** How to step to the next item, for a page that has no sibling list to
   * walk — the neighbours of the item's own kind. Falls back to stepping
   * through `itemUids`, which is what a docked panel is given. */
  stepping?: ItemStepping
  /** Show the bar every item view carries — the identifier, the stepping, the
   * saving. For a page: docked in a panel the same controls sit closer to the
   * content, and a full-width bar over a narrow panel is a page's shape. */
  pageHeader?: boolean
  itemUids?: string[]
}

export default function DisplayItemDetails({
  projectUid,
  itemUid,
  action,
  privateOpen,
  previewOpen,
  setOpen,
  setItemUid,
  setItemAction,
  setPrivateOpen,
  setPreviewOpen,
  windowed,
  pageHeader = false,
  stepping,
  itemUids,
}: DisplayItemDetailsProps): ReactElement {
  const queryClient = useQueryClient()
  const { showError } = useError()
  const rootSchema = useSchemaContext()
  const { pseudonymMode } = usePseudonym()
  const navigate = useNavigate()
  const [openedAttributes, setOpenedAttributes] = useState<
    Array<{
      schema: AttributeSchema
      attribute: Attribute<AttributeValueTypes>
      updateAttribute: (
        tag: string,
        attribute: Attribute<AttributeValueTypes>,
      ) => Attribute<AttributeValueTypes>
    }>
  >([])
  const [openedItems, setOpenedItems] = useState<
    Array<{
      identifier: string
      uid: string
      pseudonym: string | null
    }>
  >([{ identifier: '', uid: itemUid, pseudonym: null }])
  const [imageOpen, setImageOpen] = useState(false)
  const [openedImage, setOpenedImage] = useState<Image>()
  const [newTagsToSave, setNewTagsToSave] = useState<string[]>([])
  const [item, setItem] = useState<Item>()
  const [isDirty, setIsDirty] = useState(false)
  const [unsavedDialogOpen, setUnsavedDialogOpen] = useState(false)
  const [pendingNavigationUid, setPendingNavigationUid] = useState<string | null>(null)
  const [overflowAnchor, setOverflowAnchor] = useState<null | HTMLElement>(null)
  const [selectAnchor, setSelectAnchor] = useState<null | HTMLElement>(null)
  const [actionsNode, setActionsNode] = useState<null | HTMLElement>(null)
  /** Where to ask why review is wanted, while the asking is open. */
  const [flagAnchor, setFlagAnchor] = useState<{ top: number; left: number } | null>(
    null,
  )
  const [containerNode, setContainerNode] = useState<HTMLDivElement | null>(null)
  const [containerWidth, setContainerWidth] = useState<number | null>(null)
  const COMPACT_ACTIONS_THRESHOLD_PX = 600
  const compactActions =
    containerWidth !== null && containerWidth < COMPACT_ACTIONS_THRESHOLD_PX
  const closeOverflow = (): void => setOverflowAnchor(null)

  useEffect(() => {
    if (containerNode === null) return
    setContainerWidth(containerNode.clientWidth)
    const observer = new ResizeObserver((entries) => {
      const width = entries[0]?.contentRect.width
      if (width !== undefined) setContainerWidth(width)
    })
    observer.observe(containerNode)
    return () => observer.disconnect()
  }, [containerNode])

  const currentIndex = itemUids?.indexOf(itemUid) ?? -1
  const hasPrevious = itemUids !== undefined && currentIndex > 0
  const hasNext =
    itemUids !== undefined && currentIndex >= 0 && currentIndex < itemUids.length - 1

  const navigateTo = useCallback(
    (uid: string) => {
      setItemUid(uid)
      setOpenedAttributes([])
      setOpenedItems([{ identifier: '', uid, pseudonym: null }])
      setIsDirty(false)
    },
    [setItemUid],
  )

  const requestNavigation = useCallback(
    (uid: string) => {
      if (isDirty) {
        setPendingNavigationUid(uid)
        setUnsavedDialogOpen(true)
      } else {
        navigateTo(uid)
      }
    },
    [isDirty, navigateTo],
  )

  const navigatePrevious = useCallback(() => {
    if (hasPrevious && itemUids) {
      requestNavigation(itemUids[currentIndex - 1])
    }
  }, [hasPrevious, itemUids, currentIndex, requestNavigation])

  const navigateNext = useCallback(() => {
    if (hasNext && itemUids) {
      requestNavigation(itemUids[currentIndex + 1])
    }
  }, [hasNext, itemUids, currentIndex, requestNavigation])

  const itemQuery = useQuery({
    queryKey: queryKeys.item.detail(itemUid),
    queryFn: async () => {
      return await itemApi.get(itemUid)
    },
    enabled: itemUid !== undefined,
  })
  useEffect(() => {
    if (itemQuery.data !== undefined) {
      setItem(itemQuery.data)
      setIsDirty(false)
      // The item the panel opened on is only known by its uid until it
      // arrives; named here so stepping back to it can say where back is.
      setOpenedItems((opened) =>
        opened.map((entry) =>
          entry.uid === itemQuery.data.uid && entry.identifier === ''
            ? {
                identifier: itemQuery.data.identifier,
                uid: entry.uid,
                pseudonym: itemQuery.data.pseudonym,
              }
            : entry,
        ),
      )
    }
  }, [itemQuery.data])

  const changeAction = (action: ItemDetailAction): void => {
    const openedAttributesToRestore = openedAttributes
    if (action !== ItemDetailAction.VIEW && action !== ItemDetailAction.EDIT) {
      return
    }
    setItemAction(action)
    setOpenedAttributes(openedAttributesToRestore)
  }

  const handleAttributeOpen = (
    schema: AttributeSchema,
    attribute: Attribute<AttributeValueTypes>,
    updateAttribute: (
      tag: string,
      attribute: Attribute<AttributeValueTypes>,
    ) => Attribute<AttributeValueTypes>,
  ): void => {
    setOpenedAttributes([...openedAttributes, { schema, attribute, updateAttribute }])
  }

  const save = async ({ item }: { item: Item }): Promise<Item> => {
    const savedTags = await Promise.all(
      newTagsToSave.map(
        async (tag) =>
          await tagApi.save({
            uid: '00000000-0000-0000-0000-000000000000',
            name: tag,
            description: null,
            color: null,
          }),
      ),
    ).then((tags) => tags.map((tag) => tag.uid))
    item.tags = [...item.tags, ...savedTags]
    return await itemApi.save(item)
  }

  const reviewMutation = useMutation({
    mutationFn: async (status: ReviewStatus) =>
      await itemApi.setReviewStatus(itemUid, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })

  // Raised on this item and answered on the review unit above it, which is
  // what ends up flagged.
  const raiseIssueMutation = useMutation({
    mutationFn: async (reason: string) =>
      await itemApi.raiseReviewIssue(itemUid, reason),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })

  const remapMutation = useMutation({
    mutationFn: async ({ hierarchy }: { hierarchy: boolean }) => {
      if (hierarchy) {
        await itemApi.remapHierarchy(itemUid)
      } else {
        await itemApi.remap(itemUid)
      }
    },
    onSuccess: () => {
      // Remapping rewrites attribute values and revalidates, and the hierarchy
      // variant does so for descendants too, so the tables are stale as well.
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })

  /** Delete and restore are the same call: it sets whether the item is
   * selected for the project. Comment and tags are passed through unchanged,
   * since this view has no place to edit them. */
  const selectMutation = useMutation({
    mutationFn: async (value: ItemSelect) => await itemApi.select(itemUid, value),
    onSuccess: () => {
      // Deselecting cascades to children, images and observations, so every
      // item query can be affected.
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
    onError: (error) => {
      showError('Failed to change item selection', error)
    },
  })

  const saveMutation = useMutation({
    mutationFn: save,
    onSuccess: (savedItem) => {
      // Update the item in the query cache
      queryClient.setQueryData(queryKeys.item.detail(savedItem.uid), savedItem)
      // Update the item in any item list and table caches
      const updateItems = (oldData: { items: Item[]; count: number } | undefined) => {
        if (oldData === undefined) {
          return undefined
        }
        return {
          items: oldData.items.map((item: Item) =>
            item.uid === savedItem.uid ? savedItem : item,
          ),
          count: oldData.count,
        }
      }
      queryClient.setQueriesData(
        { queryKey: queryKeys.item.list(savedItem.schemaUid), exact: false },
        updateItems,
      )
      queryClient.setQueriesData(
        {
          queryKey: [...queryKeys.item.all, 'table', savedItem.schemaUid],
          exact: false,
        },
        updateItems,
      )
      // An overview is keyed by the item it is of, not by the item saved here,
      // so it cannot be patched the way the lists above are: it is asked for
      // again. The panel is usually open beside one showing what was edited.
      void queryClient.invalidateQueries({
        predicate: (query) => query.queryKey.includes('overview'),
      })
      // Stays editable: saving is a checkpoint in the middle of curating an
      // item, not the end of it.
      setIsDirty(false)
    },
  })

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.ctrlKey && event.key === ',') {
        event.preventDefault()
        navigatePrevious()
      } else if (event.ctrlKey && event.key === '.') {
        event.preventDefault()
        navigateNext()
      } else if (event.ctrlKey && event.key === 's') {
        event.preventDefault()
        if (action === ItemDetailAction.EDIT && item) {
          saveMutation.mutate({ item })
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [navigatePrevious, navigateNext, action, item, saveMutation])

  if (item === undefined || itemQuery.data === undefined) {
    if (itemQuery.isLoading) {
      return <LinearProgress />
    } else {
      return <></>
    }
  }

  const handleSave = (): void => {
    saveMutation.mutate({ item })
  }

  const handleAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    const updatedAttributes = { ...item.attributes }
    updatedAttributes[tag] = attribute
    const updatedItem = { ...item, attributes: updatedAttributes }
    setItem(updatedItem)
    setIsDirty(true)
  }

  const handlePrivateAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    const updatedAttributes = { ...item.privateAttributes }
    updatedAttributes[tag] = attribute
    const updatedItem = { ...item, privateAttributes: updatedAttributes }
    setItem(updatedItem)
    setIsDirty(true)
  }

  const handleIdentifierUpdate = (identifier: string): void => {
    const updatedItem = { ...item }
    updatedItem.identifier = identifier
    setItem(updatedItem)
    setIsDirty(true)
  }

  const handleNameUpdate = (name: string): void => {
    const updatedItem = { ...item }
    updatedItem.name = name
    setItem(updatedItem)
    setIsDirty(true)
  }

  const handleCommentUpdate = (comment: string): void => {
    const updatedItem = { ...item }
    updatedItem.comment = comment
    setItem(updatedItem)
    setIsDirty(true)
  }

  const handleTagsUpdate = (tags: string[]): void => {
    const updatedItem = { ...item, tags }
    setItem(updatedItem)
    setIsDirty(true)
  }

  const handleNestedAttributeChange = (uid?: string): void => {
    if (uid === undefined) {
      setOpenedAttributes([])
      return
    }
    const parentAttributeIndex = openedAttributes.findIndex(
      (attribute) => attribute.attribute.uid === uid,
    )
    if (parentAttributeIndex >= 0) {
      setOpenedAttributes(openedAttributes.slice(0, parentAttributeIndex + 1))
    }
  }

  const handleChangeItem = (
    name: string,
    uid: string,
    pseudonym?: string | null,
  ): void => {
    setItemUid(uid)
    const existingIndex = openedItems.findIndex((i) => i.uid === uid)
    if (existingIndex >= 0) {
      setOpenedItems(openedItems.slice(0, existingIndex + 1))
    } else {
      setOpenedItems([
        ...openedItems,
        { identifier: name, uid: uid, pseudonym: pseudonym ?? null },
      ])
    }
  }

  function handleOpenImageChange(image: Image): void {
    setOpenedImage(image)
    setImageOpen(true)
  }

  const itemSchema = (function () {
    switch (item.itemValueType) {
      case ItemValueType.SAMPLE:
        return rootSchema.samples[item.schemaUid]
      case ItemValueType.IMAGE:
        return rootSchema.images[item.schemaUid]
      case ItemValueType.OBSERVATION:
        return rootSchema.observations[item.schemaUid]
      case ItemValueType.ANNOTATION:
        return rootSchema.annotations[item.schemaUid]
      default:
        throw new Error('Unknown item value type')
    }
  })()

  const nestedAttributesOpened = openedAttributes.length > 0

  // Following a relation opens that item in place of this one; this is the way
  // back out, a step at a time. Only the step just taken is offered — a trail
  // of everything passed through on the way says more than it is worth.
  const previousItem = openedItems[openedItems.length - 2]
  const back =
    previousItem === undefined
      ? undefined
      : {
          identifier:
            getDisplayIdentifier(previousItem, pseudonymMode) || 'the previous item',
          go: () => {
            setOpenedItems(openedItems.slice(0, -1))
            setItemUid(previousItem.uid)
          },
        }

  return (
    <Spinner loading={itemQuery.isLoading}>
      <Box ref={setContainerNode} sx={{ width: '100%', minWidth: 0 }}>
        {/* The same bar every other view of an item carries. */}
        {pageHeader && item !== undefined && (
          <ItemViewHeader
            identifier={getDisplayIdentifier(item, pseudonymMode)}
            onPrevious={stepping?.onPrevious ?? navigatePrevious}
            onNext={stepping?.onNext ?? navigateNext}
            hasPrevious={stepping?.hasPrevious ?? hasPrevious}
            hasNext={stepping?.hasNext ?? hasNext}
            edit={
              action === ItemDetailAction.EDIT
                ? {
                    isDirty,
                    saving: saveMutation.isPending,
                    save: handleSave,
                    revert: () => {
                      setItem(itemQuery.data)
                      setIsDirty(false)
                    },
                  }
                : undefined
            }
          >
            {back !== undefined && (
              <Tooltip title={`Back to ${back.identifier}`}>
                <IconButton onClick={back.go} size="small">
                  <ArrowBack fontSize="small" />
                </IconButton>
              </Tooltip>
            )}
          </ItemViewHeader>
        )}
        <Card>
          {/* A titled strip along the top, so the panel reads as a panel: it
              says what it holds and carries the close where a panel's close
              belongs, rather than floating an ✗ over the first row. */}
          {!pageHeader && (
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 1,
                pl: 2,
                pr: 1,
                py: 0.5,
                borderBottom: 1,
                borderColor: 'divider',
              }}
            >
              {back !== undefined && (
                <Tooltip title={`Back to ${back.identifier}`}>
                  <IconButton onClick={back.go} size="small" sx={{ ml: -1 }}>
                    <ArrowBack fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              <Typography variant="subtitle2" noWrap sx={{ flex: 1, minWidth: 0 }}>
                {itemSchema.displayName}
              </Typography>
              <Tooltip title="Close">
                <IconButton onClick={() => setOpen(false)} size="small">
                  <Close fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          )}
          <CardContent>
            <Grid container>
              <Grid size="grow">
                {!nestedAttributesOpened ? (
                  <Stack spacing={1}>
                    <DisplayItemIdentifiers
                      item={item}
                      action={action}
                      direction="row"
                      handleIdentifierUpdate={handleIdentifierUpdate}
                      handleNameUpdate={handleNameUpdate}
                      handleCommentUpdate={handleCommentUpdate}
                    />

                    <DisplayItemTags
                      tagUids={item.tags}
                      newTagNames={newTagsToSave}
                      editable={action !== ItemDetailAction.VIEW}
                      handleTagsUpdate={handleTagsUpdate}
                      setNewTags={setNewTagsToSave}
                    />
                    <ChipDivider
                      label="Relations"
                      color={item.validRelations ? 'default' : 'error'}
                    />

                    <ItemLinkage
                      item={item}
                      action={action}
                      handleItemOpen={handleChangeItem}
                      setItem={setItem}
                    />

                    {isImageItem(item) && (
                      <React.Fragment>
                        <ChipDivider label="Thumbnails" color="primary" />
                        <Thumbnail
                          image={item}
                          openImage={handleOpenImageChange}
                          size={{ width: 512, height: 512 }}
                        />
                      </React.Fragment>
                    )}
                    {Object.keys(item.attributes).length > 0 && (
                      <React.Fragment>
                        <ChipDivider
                          label="Attributes"
                          color={item.validAttributes ? 'default' : 'error'}
                        />
                        <AttributeDetails
                          schemas={itemSchema.attributes}
                          attributes={item.attributes}
                          action={action}
                          attributeLayout={itemSchema.attributeLayout}
                          handleAttributeOpen={handleAttributeOpen}
                          handleAttributeUpdate={handleAttributeUpdate}
                        />
                      </React.Fragment>
                    )}
                  </Stack>
                ) : (
                  <NestedAttributeDetails
                    openedAttributes={openedAttributes}
                    action={action}
                    handleNestedAttributeChange={handleNestedAttributeChange}
                    handleAttributeOpen={handleAttributeOpen}
                    handleAttributeUpdate={handleAttributeUpdate}
                  />
                )}
              </Grid>
              {(privateOpen || previewOpen) && (
                <Grid size={{ xs: 6 }}>
                  {previewOpen && (
                    <Stack spacing={1}>
                      <ChipDivider label="Preview" color="primary" />

                      <DisplayPreview showPreview={previewOpen} itemUid={item.uid} />
                    </Stack>
                  )}
                  {privateOpen && (
                    <Stack spacing={1}>
                      <ChipDivider label="Private Attributes" color="secondary" />
                      <Box sx={{ maxHeight: '70vh', overflow: 'auto' }}>
                        <AttributeDetails
                          schemas={itemSchema.privateAttributes}
                          attributes={item.privateAttributes}
                          action={action}
                          attributeLayout={itemSchema.privateAttributeLayout}
                          handleAttributeOpen={handleAttributeOpen}
                          handleAttributeUpdate={handlePrivateAttributeUpdate}
                          spacing={2}
                        />
                      </Box>
                    </Stack>
                  )}
                </Grid>
              )}
            </Grid>
          </CardContent>
          {/* Spaced by a gap rather than by CardActions' own left margins:
              those are put on every child but the first, so a wrapped row
              starts indented while the row above it does not. */}
          <CardActions
            disableSpacing
            ref={setActionsNode}
            sx={{ flexWrap: 'wrap', gap: 0.5, alignItems: 'center' }}
          >
            {!pageHeader && (
              <>
                <Tooltip title="Previous item (Ctrl+,)">
                  <span>
                    <IconButton disabled={!hasPrevious} onClick={navigatePrevious}>
                      <ChevronLeft />
                    </IconButton>
                  </span>
                </Tooltip>
                <Tooltip title="Next item (Ctrl+.)">
                  <span>
                    <IconButton disabled={!hasNext} onClick={navigateNext}>
                      <ChevronRight />
                    </IconButton>
                  </span>
                </Tooltip>
              </>
            )}
            {/* Stepping through the items is the only thing on the left; what
                acts on the item on screen is gathered on the right, ending in
                the menu that holds the rest of it. */}
            <span style={{ flex: 1 }} />
            {!pageHeader && action === ItemDetailAction.EDIT && (
              <React.Fragment>
                <Tooltip title="Discard changes">
                  <span>
                    <IconButton
                      disabled={!isDirty}
                      onClick={() => {
                        setItem(itemQuery.data)
                        setIsDirty(false)
                      }}
                    >
                      <Undo />
                    </IconButton>
                  </span>
                </Tooltip>
                <Tooltip title="Save (Ctrl+S)">
                  <span>
                    <IconButton disabled={!isDirty} onClick={handleSave}>
                      <Save />
                    </IconButton>
                  </span>
                </Tooltip>
              </React.Fragment>
            )}
            {action === ItemDetailAction.VIEW && (
              <Button
                size="small"
                sx={{ ml: 0.5 }}
                onClick={() => {
                  changeAction(ItemDetailAction.EDIT)
                }}
              >
                Edit
              </Button>
            )}
            {(() => {
              const remapActions: ItemAction[] =
                action === ItemDetailAction.EDIT
                  ? [
                      {
                        key: 'remap-this',
                        icon: <AutoFixNormal />,
                        label: 'Re-apply mappers to this item',
                        onClick: () => remapMutation.mutate({ hierarchy: false }),
                        disabled: remapMutation.isPending,
                      },
                      {
                        key: 'remap-tree',
                        icon: <AutoFixHigh />,
                        label: 'Re-apply mappers to this item and all descendants',
                        onClick: () => remapMutation.mutate({ hierarchy: true }),
                        disabled: remapMutation.isPending,
                      },
                    ]
                  : []
              // The icon is the action, not the item's state, and its colour is
              // the state the action moves the item into: red to raise, green
              // to mark reviewed.
              //
              // Raising is offered wherever a unit above answers for the item,
              // which is most of the hierarchy; working through the queue and
              // signing off belong to the unit itself.
              const raiseAction: ItemAction[] =
                isUnderReviewUnit(rootSchema, itemSchema.uid) && item !== undefined
                  ? [
                      {
                        key: 'flag',
                        icon: <Flag sx={{ color: 'error.main', opacity: 0.7 }} />,
                        label: 'Flag for review',
                        onClick: (event?: React.MouseEvent<HTMLElement>) => {
                          // A position rather than an element: picked from the
                          // overflow menu there is no button left to measure,
                          // so the action strip stands in for it.
                          const anchor = event?.currentTarget ?? actionsNode
                          const rect = anchor?.getBoundingClientRect()
                          setFlagAnchor(
                            rect !== undefined
                              ? {
                                  top: rect.bottom,
                                  left: rect.left + rect.width / 2,
                                }
                              : {
                                  top: window.innerHeight / 2,
                                  left: window.innerWidth / 2,
                                },
                          )
                        },
                        disabled: raiseIssueMutation.isPending,
                      },
                    ]
                  : []
              const reviewActions: ItemAction[] =
                isReviewUnit(rootSchema, itemSchema.uid) && item !== undefined
                  ? [
                      // Into the view that works through these one at a time,
                      // stopped on this one. In a window of its own the panel has
                      // no room for it, so it gets a tab of its own instead.
                      {
                        key: 'open-review',
                        icon: <RateReview />,
                        label: 'Open in review',
                        onClick: () => {
                          const path = `/project/${projectUid}/review?openItem=${item.uid}`
                          if (windowed) {
                            window.open(path, '_blank', 'noopener,noreferrer')
                          } else {
                            navigate(path)
                          }
                        },
                      },
                      ...(item.reviewStatus === ReviewStatus.Flagged
                        ? [
                            {
                              key: 'reviewed',
                              icon: (
                                <Flag sx={{ color: 'success.main', opacity: 0.7 }} />
                              ),
                              // What it was flagged for is what is open on
                              // it, which the review view lists; the item is
                              // where it is dealt with rather than read.
                              label: 'Mark as reviewed',
                              onClick: () => {
                                reviewMutation.mutate(ReviewStatus.Reviewed)
                              },
                              disabled: reviewMutation.isPending,
                            },
                          ]
                        : []),
                    ]
                  : []

              // What the panel shows of the item, and where else the item can
              // be seen: looking at something is undone by looking away, so
              // these stay on the strip whenever there is room for them.
              const showActions: ItemAction[] = [
                {
                  key: 'private',
                  icon: <Security />,
                  label: 'Private attributes',
                  onClick: () => {
                    setPreviewOpen(false)
                    setPrivateOpen(!privateOpen)
                  },
                  disabled: Object.keys(itemSchema.privateAttributes).length === 0,
                },
                {
                  key: 'preview',
                  icon: <Preview />,
                  label: 'Preview',
                  onClick: () => {
                    setPrivateOpen(false)
                    setPreviewOpen(!previewOpen)
                  },
                },
                // The views of the item are links: a click goes there, and the
                // browser keeps its own middle-click, ctrl-click and "open in
                // new window" for anyone who wants one beside the panel. They
                // are named and ordered as the bar names them, since they are
                // the same set of views.
                //
                // What the panel is showing, on a page of its own. Left out on
                // that page: it is where the link goes.
                ...(!windowed && !pageHeader
                  ? [
                      {
                        key: 'item-page',
                        icon: <Notes />,
                        label: 'Details',
                        href: `/project/${projectUid}/item/${item.uid}`,
                      },
                    ]
                  : []),
                // Every layout the schema lists is a way into an item; one
                // written to be read beside another is not listed, but nested
                // in whatever composes it.
                ...rootSchema.overviewLayouts
                  .filter((layout) => layout.schemaUid === item.schemaUid)
                  .map((layout) => ({
                    key: `layout-${layout.uid}`,
                    icon: <TableChart />,
                    label: layout.displayName,
                    href: `/project/${projectUid}/item/${item.uid}/overview/${layout.uid}`,
                  })),
                // What hangs under the item, on the same terms.
                ...rootSchema.hierarchyLayouts
                  .filter((layout) => layout.schemaUid === item.schemaUid)
                  .map((layout) => ({
                    key: `hierarchy-${layout.uid}`,
                    icon: <AccountTree />,
                    label: layout.displayName,
                    href: `/project/${projectUid}/item/${item.uid}/hierarchy/${layout.uid}`,
                  })),
                {
                  key: 'images',
                  icon: <PhotoLibrary />,
                  label: 'Images',
                  href: `/project/${projectUid}/images_for_item/${item.uid}`,
                },
              ]
              // What changes the item — re-mapping it, taking it out of the
              // project — is rare and is not undone by looking away, so it
              // stays in the menu at every width rather than sitting a
              // mis-click from the buttons that only show something.
              const changeActions: ItemAction[] = [
                ...remapActions,
                {
                  key: 'select',
                  icon: item.selected ? <Delete /> : <RestoreFromTrash />,
                  label: item.selected ? 'Delete from project' : 'Restore to project',
                  // Confirmed in the same popover the tables use, which also
                  // collects the comment and tags to record with it.
                  onClick: (event) => {
                    setSelectAnchor(event?.currentTarget ?? actionsNode)
                  },
                  disabled: selectMutation.isPending,
                },
              ]
              // Review stays out of the overflow at every width: the panel is
              // usually docked and narrow, so folding it away would put the
              // flags behind a menu exactly where they are used most. Narrow,
              // it is the only thing left on the strip.
              const strip = compactActions
                ? [...raiseAction, ...reviewActions]
                : [...showActions, ...raiseAction, ...reviewActions]
              const menu = compactActions
                ? [...showActions, ...changeActions]
                : changeActions
              return (
                <React.Fragment>
                  {strip.map((entry) => (
                    <Tooltip disableInteractive key={entry.key} title={entry.label}>
                      <span>
                        <IconButton
                          onClick={entry.onClick}
                          disabled={entry.disabled}
                          {...(entry.href !== undefined
                            ? { component: RouterLink, to: entry.href }
                            : {})}
                        >
                          {entry.icon}
                        </IconButton>
                      </span>
                    </Tooltip>
                  ))}
                  <IconButton onClick={(e) => setOverflowAnchor(e.currentTarget)}>
                    <MoreVert />
                  </IconButton>
                  <Menu
                    anchorEl={overflowAnchor}
                    open={Boolean(overflowAnchor)}
                    onClose={closeOverflow}
                  >
                    {menu.map((entry, index) => [
                      // Ruled off from whatever is above it, so what changes
                      // the item is not read as more of the same list.
                      index > 0 && entry.key === changeActions[0]?.key ? (
                        <Divider key={`${entry.key}-divider`} />
                      ) : null,
                      <MenuItem
                        key={entry.key}
                        disabled={entry.disabled}
                        {...(entry.href !== undefined
                          ? { component: RouterLink, to: entry.href }
                          : {})}
                        onClick={() => {
                          closeOverflow()
                          entry.onClick?.()
                        }}
                      >
                        <ListItemIcon>{entry.icon}</ListItemIcon>
                        <ListItemText>{entry.label}</ListItemText>
                      </MenuItem>,
                    ])}
                  </Menu>
                </React.Fragment>
              )
            })()}
          </CardActions>
        </Card>
      </Box>

      {openedImage !== undefined && (
        <ImageViewerDialog
          open={imageOpen}
          image={openedImage}
          setOpen={setImageOpen}
        />
      )}

      {selectAnchor !== null && item !== undefined && (
        <ItemSelectPopover
          anchorEl={selectAnchor}
          select={!item.selected}
          subject={getDisplayIdentifier(item, pseudonymMode)}
          comment={item.comment}
          tags={item.tags}
          additiveTags={false}
          onClose={() => setSelectAnchor(null)}
          onConfirm={(value) => {
            selectMutation.mutate(value)
            setSelectAnchor(null)
            // The row is gone from the table, so the panel would be showing an
            // item that is no longer in the list it navigates.
            setOpen(false)
          }}
        />
      )}

      <Dialog open={unsavedDialogOpen} onClose={() => setUnsavedDialogOpen(false)}>
        <DialogTitle>Unsaved changes</DialogTitle>
        <DialogContent>
          <DialogContentText>
            You have unsaved changes. What would you like to do?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUnsavedDialogOpen(false)}>Cancel</Button>
          <Button
            onClick={() => {
              setUnsavedDialogOpen(false)
              setItem(itemQuery.data)
              setIsDirty(false)
              if (pendingNavigationUid) {
                navigateTo(pendingNavigationUid)
                setPendingNavigationUid(null)
              }
            }}
          >
            Discard
          </Button>
          <Button
            onClick={() => {
              setUnsavedDialogOpen(false)
              if (item) {
                saveMutation.mutate(
                  { item },
                  {
                    onSuccess: () => {
                      if (pendingNavigationUid) {
                        navigateTo(pendingNavigationUid)
                        setPendingNavigationUid(null)
                      }
                    },
                  },
                )
              }
            }}
          >
            Save
          </Button>
        </DialogActions>
      </Dialog>
      {flagAnchor !== null && (
        <ReviewFlagPopover
          anchorPosition={flagAnchor}
          count={1}
          onClose={() => setFlagAnchor(null)}
          onConfirm={(reason) => {
            raiseIssueMutation.mutate(reason ?? '')
            setFlagAnchor(null)
          }}
        />
      )}
    </Spinner>
  )
}
