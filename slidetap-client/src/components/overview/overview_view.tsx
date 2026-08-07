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
  Add,
  ChevronLeft,
  ChevronRight,
  Delete,
  DragHandle,
  DragIndicator,
  FileCopy,
  Save,
  Undo,
} from '@mui/icons-material'
import {
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  LinearProgress,
  Menu,
  MenuItem,
  Stack,
  TextField,
  Tooltip,
  Typography,
  useMediaQuery,
  type Theme,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactElement,
} from 'react'
import AttributeDetails from 'src/components/attribute/attribute_details'
import EditItemDialog from 'src/components/item/edit_item_dialog'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { ItemDetailAction } from 'src/models/action'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import { AttributeValueType } from 'src/models/attribute_value_type'
import type { OverviewItem, OverviewSection } from 'src/models/overview'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import type {
  AttributeGroupLayout,
  AttributeSchema,
  ObjectAttributeSchema,
} from 'src/models/schema/attribute_schema'
import type {
  OverviewLayout,
  OverviewSectionLayout,
} from 'src/models/schema/overview_layout'
import type { TableRequest } from 'src/models/table_item'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'
import { getContainerSpanSx } from 'src/components/container_span'
import { ValueActions, type ValueAction } from 'src/components/table/value_actions'

/** Each panel scrolls itself, with no bar drawn: one that appears and
 * disappears takes width from the column as it does, reflowing the cards
 * whenever content crosses the height of the panel. */
const panelScrollSx = {
  overflowY: 'auto',
  scrollbarWidth: 'none',
  '&::-webkit-scrollbar': { display: 'none' },
} as const

/** What a header outside the overview needs to save and revert for it. */
export interface OverviewEditState {
  isDirty: boolean
  saving: boolean
  save: () => void
  revert: () => void
}

interface OverviewViewProps {
  projectUid: string
  itemUid: string
  overviewLayout: OverviewLayout
  batchUid?: string
  tableRequest?: TableRequest
  /** Open an item somewhere outside the overview — a docked detail panel. The
   * siblings are every item the overview shows, in reading order, so whatever
   * opens it can step through them. */
  onOpenItem?: (itemUid: string, siblingUids: string[]) => void
  /** The one currently open, marked so it can be told from the rest. */
  openedItemUid?: string | null
  /** Leave out the bar with the identifier and the navigation, for a caller
   * that has one of its own — two bars naming the same case and stepping
   * through it in two different orders is one too many. Take
   * `onEditStateChange` with it, or saving is left without a button. */
  hideHeader?: boolean
  /** Reports what the save and revert buttons need, whenever it changes. */
  onEditStateChange?: (state: OverviewEditState) => void
}

export default function OverviewView({
  projectUid,
  itemUid,
  overviewLayout,
  batchUid,
  tableRequest,
  onOpenItem,
  openedItemUid,
  hideHeader = false,
  onEditStateChange,
}: OverviewViewProps): ReactElement {
  const { pseudonymMode } = usePseudonym()
  const queryClient = useQueryClient()
  const rootSchema = useSchemaContext()
  const [currentItemUid, setCurrentItemUid] = useState(itemUid)
  const [editedItems, setEditedItems] = useState<
    Record<string, Record<string, Attribute<AttributeValueTypes>>>
  >({})
  const [editDialogItemUid, setEditDialogItemUid] = useState<string | null>(null)

  useEffect(() => {
    setCurrentItemUid(itemUid)
    setEditedItems({})
  }, [itemUid])

  const overviewQuery = useQuery({
    queryKey: [
      ...queryKeys.item.overview(currentItemUid, overviewLayout.uid),
      pseudonymMode,
      batchUid ?? null,
      tableRequest ?? null,
    ],
    queryFn: () =>
      itemApi.getOverviewRoot(
        currentItemUid,
        overviewLayout.uid,
        pseudonymMode,
        batchUid,
        tableRequest,
      ),
  })

  const hasPrevious = overviewQuery.data?.previousUid != null
  const hasNext = overviewQuery.data?.nextUid != null

  const navigateTo = useCallback((uid: string) => {
    setCurrentItemUid(uid)
    setEditedItems({})
  }, [])

  const navigatePrevious = useCallback(() => {
    if (overviewQuery.data?.previousUid) {
      navigateTo(overviewQuery.data.previousUid)
    }
  }, [overviewQuery.data?.previousUid, navigateTo])

  const navigateNext = useCallback(() => {
    if (overviewQuery.data?.nextUid) {
      navigateTo(overviewQuery.data.nextUid)
    }
  }, [overviewQuery.data?.nextUid, navigateTo])

  // Build a map of all target schemas from sections
  const allSchemas = {
    ...rootSchema.observations,
    ...rootSchema.samples,
    ...rootSchema.images,
    ...rootSchema.annotations,
  }

  // Save a single target item
  const saveItemMutation = useMutation({
    mutationFn: async ({
      targetItemUid,
      attributes,
    }: {
      targetItemUid: string
      attributes: Record<string, Attribute<AttributeValueTypes>>
    }) => {
      const existingItem = await itemApi.get(targetItemUid)
      const itemSchema = allSchemas[existingItem.schemaUid]
      const updatedItem = applyEditsToItem(existingItem, attributes, itemSchema)
      return await itemApi.save(updatedItem)
    },
  })

  const invalidateOverview = useCallback(() => {
    queryClient.invalidateQueries({
      queryKey: queryKeys.item.overview(currentItemUid, overviewLayout.uid),
    })
  }, [queryClient, currentItemUid, overviewLayout.uid])

  const addChildMutation = useMutation({
    mutationFn: async ({
      schemaUid,
      parentItemUid,
      identifier,
    }: {
      schemaUid: string
      parentItemUid: string
      identifier: string
    }) => {
      const batchUid = overviewQuery.data?.batchUid
      if (!batchUid) {
        throw new Error('Cannot add item before overview is loaded')
      }
      return itemApi.create(schemaUid, batchUid, [parentItemUid], identifier)
    },
    onSuccess: (created) => {
      invalidateOverview()
      if (created) setEditDialogItemUid(created.uid)
    },
  })

  const copyToParentMutation = useMutation({
    mutationFn: async ({
      itemUid,
      targetParentUid,
      identifier,
    }: {
      itemUid: string
      targetParentUid: string
      identifier: string
    }) => itemApi.copy(itemUid, [targetParentUid], identifier),
    onSuccess: (created) => {
      invalidateOverview()
      if (created) setEditDialogItemUid(created.uid)
    },
  })

  const deleteGroupMutation = useMutation({
    mutationFn: async ({ itemUid }: { itemUid: string }) =>
      itemApi.select(itemUid, {
        select: false,
        comment: null,
        tags: null,
        additiveTags: false,
      }),
    onSuccess: invalidateOverview,
  })

  const moveAttributeMutation = useMutation({
    mutationFn: async ({
      sourceItemUid,
      attributeTag,
      targetItemUid,
    }: {
      sourceItemUid: string
      attributeTag: string
      targetItemUid: string
    }) => await itemApi.moveAttribute(sourceItemUid, attributeTag, targetItemUid),
    onSuccess: invalidateOverview,
  })

  /** Moves the item itself to another item, with everything on it — as opposed
   * to moveAttribute, which swaps a single value between two items. */
  const moveItemMutation = useMutation({
    mutationFn: async ({
      itemUid,
      targetParentUid,
    }: {
      itemUid: string
      targetParentUid: string
    }) => await itemApi.move(itemUid, targetParentUid),
    onSuccess: invalidateOverview,
  })

  const handleAttributeUpdate = useCallback(
    (targetItemUid: string, tag: string, attribute: Attribute<AttributeValueTypes>) => {
      setEditedItems((prev) => ({
        ...prev,
        [targetItemUid]: {
          ...(prev[targetItemUid] ?? {}),
          [tag]: attribute,
        },
      }))
    },
    [],
  )

  const handleSaveAll = useCallback(async () => {
    if (saveItemMutation.isPending) return
    const entries = Object.entries(editedItems)
    if (entries.length === 0) return
    try {
      await Promise.all(
        entries.map(([targetItemUid, attributes]) =>
          saveItemMutation.mutateAsync({ targetItemUid, attributes }),
        ),
      )
      setEditedItems({})
      queryClient.invalidateQueries({
        queryKey: queryKeys.item.overview(currentItemUid, overviewLayout.uid),
      })
    } catch {
      // Keep editedItems intact so user can retry
    }
  }, [editedItems, saveItemMutation, queryClient, currentItemUid, overviewLayout.uid])

  const isDirty = Object.keys(editedItems).length > 0

  // Through a ref rather than as a dependency: `handleSaveAll` is rebuilt on
  // every render, and reporting it would have the state it is reported to
  // trigger the render that rebuilds it.
  const saveRef = useRef(handleSaveAll)
  useEffect(() => {
    saveRef.current = handleSaveAll
  })
  const save = useCallback(() => {
    void saveRef.current()
  }, [])
  const revert = useCallback(() => setEditedItems({}), [])

  useEffect(() => {
    onEditStateChange?.({
      isDirty,
      saving: saveItemMutation.isPending,
      save,
      revert,
    })
  }, [onEditStateChange, isDirty, saveItemMutation.isPending, save, revert])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      // Stepping belongs to whoever draws the header. Without this the keys
      // would move the overview to a case the caller's list knows nothing of.
      if (event.ctrlKey && event.key === ',' && !hideHeader) {
        event.preventDefault()
        navigatePrevious()
      } else if (event.ctrlKey && event.key === '.' && !hideHeader) {
        event.preventDefault()
        navigateNext()
      } else if (event.ctrlKey && event.key === 's') {
        event.preventDefault()
        handleSaveAll()
      } else if (event.ctrlKey && event.key === 'z') {
        event.preventDefault()
        if (!saveItemMutation.isPending) {
          setEditedItems({})
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [
    navigatePrevious,
    navigateNext,
    handleSaveAll,
    saveItemMutation.isPending,
    hideHeader,
  ])

  // Narrow enough and the two columns become one. That is not only a matter of
  // direction: stacked there is a single page-length scroll and the cards grow
  // to their content, where side by side each column is a fixed-height panel
  // that scrolls on its own and the cards divide the height between them.
  const sideBySide = useMediaQuery((theme: Theme) => theme.breakpoints.up('md'))

  if (overviewQuery.isLoading) {
    return <LinearProgress />
  }

  if (!overviewQuery.data) {
    return <Typography>No data available</Typography>
  }

  // Every item the overview shows, in the order they are read, so whatever
  // opens one can step through the case the same way the eye does.
  const orderedItemUids = Array.from(
    new Set(
      overviewQuery.data.sections.flatMap((group) => [
        ...(group.parentItem !== null ? [group.parentItem.itemUid] : []),
        ...group.items.map((item) => item.itemUid),
      ]),
    ),
  )

  /** Opening an item while the overview holds unsaved edits for it would leave
   * two editors on one item, so the way in is closed until those are saved. */
  const openItem = (uid: string): (() => void) | undefined => {
    if (onOpenItem === undefined || editedItems[uid] !== undefined) return undefined
    return () => onOpenItem(uid, orderedItemUids)
  }

  /** A chip that cannot be opened says nothing about why, so a blocked one
   * carries a disabled action whose tooltip does. */
  const openBlockedAction = (uid: string): ValueAction[] | undefined => {
    if (onOpenItem === undefined || editedItems[uid] === undefined) return undefined
    return [
      {
        key: 'open-blocked',
        icon: <ChevronRight fontSize="small" />,
        label: 'Save the changes to this item before opening it',
        onClick: () => {},
        disabled: true,
      },
    ]
  }

  // Sections marked aside get a column of their own; the rest share the grid
  // beside it. The aside takes the width it asks for, out of twelve.
  const asideSections = overviewLayout.sections.filter((section) => section.aside)
  const mainSections = overviewLayout.sections.filter((section) => !section.aside)
  const asideWidth = asideSections[0]?.width
  const asideSpan = asideWidth?.lg ?? asideWidth?.md ?? asideWidth?.xs ?? 4

  const renderSectionCards = (
    section: OverviewSectionLayout,
    inGrid: boolean,
  ): ReactElement[] | null => {
    const sectionData = overviewQuery.data?.sections.filter(
      (group) => group.schemaUid === section.schemaUid,
    )
    if (sectionData === undefined || sectionData.length === 0) {
      return null
    }
    // Only the grid column places cards by span; the aside is a single column.
    const sectionSx = inGrid ? getContainerSpanSx(section.width, section.expand) : undefined
    return sectionData.map((group) => (
      <Box
        key={group.itemUid}
        sx={{
          ...sectionSx,
          ...(section.aside && sideBySide && { flex: '1 1 0', minHeight: 0 }),
        }}
      >
        <OverviewSectionCard
          group={group}
          allSchemas={allSchemas}
          targetAttributes={[...section.attributes, ...section.privateAttributes]}
          section={section}
          siblingGroups={sectionData}
          editedItems={editedItems}
          onAttributeUpdate={handleAttributeUpdate}
          onAddChild={(parentItemUid, identifier) =>
            addChildMutation.mutate({
              schemaUid: section.schemaUid,
              parentItemUid,
              identifier,
            })
          }
          onCopyToParent={(itemUid, targetParentUid, identifier) =>
            copyToParentMutation.mutate({ itemUid, targetParentUid, identifier })
          }
          onMoveAttribute={(sourceItemUid, attributeTag, targetItemUid) => {
            moveAttributeMutation.mutate({ sourceItemUid, attributeTag, targetItemUid })
          }}
          onMoveItem={(itemUid, targetParentUid) => {
            moveItemMutation.mutate({ itemUid, targetParentUid })
          }}
          onDelete={(groupItemUid) => deleteGroupMutation.mutate({ itemUid: groupItemUid })}
          fillHeight={section.aside && sideBySide}
          openItem={openItem}
          openBlockedAction={openBlockedAction}
          openedItemUid={openedItemUid}
          isMutating={
            addChildMutation.isPending ||
            copyToParentMutation.isPending ||
            moveAttributeMutation.isPending ||
            moveItemMutation.isPending ||
            deleteGroupMutation.isPending
          }
        />
      </Box>
    ))
  }

  return (
    // A column, so the section row below the header can take the height that is
    // left and bound its own scrolling. Without it the row grows to its content
    // and the window scrolls instead of the panels.
    <Box
      sx={{
        height: '100%',
        minHeight: 0,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Navigation header — full width */}
      {/* Never gives up height: it is a fixed bar, and the column below it can
          always scroll instead. */}
      {!hideHeader && (
      <Card sx={{ mb: 2, flexShrink: 0 }}>
        <CardContent
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            py: 1,
            '&:last-child': { pb: 1 },
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 80 }}>
            <Tooltip title="Previous (Ctrl+,)">
              <span>
                <Button disabled={!hasPrevious} onClick={navigatePrevious} size="small">
                  <ChevronLeft />
                </Button>
              </span>
            </Tooltip>
          </Box>
          {/* The case is an item like the rest, so its identifier opens and
              copies the same way theirs do. */}
          <Box sx={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
            <ValueActions
              value={getDisplayIdentifier(
                {
                  uid: overviewQuery.data.itemUid,
                  identifier: overviewQuery.data.identifier,
                  pseudonym: overviewQuery.data.pseudonym,
                },
                pseudonymMode,
              )}
              monospace
              copyable
              copyLabel="Copy case identifier"
              onOpen={openItem(overviewQuery.data.itemUid)}
              actions={openBlockedAction(overviewQuery.data.itemUid)}
            />
          </Box>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              minWidth: 120,
              gap: 0.5,
            }}
          >
            <Tooltip title="Revert all changes (Ctrl+Z)">
              <span>
                <Button
                  onClick={() => setEditedItems({})}
                  size="small"
                  disabled={!isDirty || saveItemMutation.isPending}
                >
                  <Undo />
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="Save all (Ctrl+S)">
              <span>
                <Button
                  onClick={handleSaveAll}
                  size="small"
                  disabled={!isDirty || saveItemMutation.isPending}
                  color="primary"
                >
                  <Save />
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="Next (Ctrl+.)">
              <span>
                <Button disabled={!hasNext} onClick={navigateNext} size="small">
                  <ChevronRight />
                </Button>
              </span>
            </Tooltip>
          </Box>
        </CardContent>
      </Card>
      )}

      <Box
        sx={{
          display: 'flex',
          flexDirection: sideBySide ? 'row' : 'column',
          alignItems: 'stretch',
          gap: 1.5,
          // Takes the height left by the navigation header, so the columns
          // scroll inside it instead of the page scrolling as a whole. Once
          // they are stacked there is only one column, and that one scroll is
          // this one. Basis zero rather than content: stacked, its content runs
          // far past the window, and a content-sized basis would have it push
          // against the bar above instead of scrolling.
          flex: '1 1 0',
          minHeight: 0,
          ...(!sideBySide && panelScrollSx),
        }}
      >
        {asideSections.length > 0 && (
          // Scrolls on its own, so reading the report does not move the items
          // and working through the items does not move the report.
          <Box
            sx={{
              width: sideBySide ? `${(asideSpan / 12) * 100}%` : '100%',
              flexShrink: 0,
              minHeight: 0,
              ...(sideBySide && { maxHeight: '100%', ...panelScrollSx }),
              display: 'flex',
              flexDirection: 'column',
              gap: 1.5,
            }}
          >
            {asideSections.map((section) => renderSectionCards(section, false))}
          </Box>
        )}
        <Box
          sx={{
            flex: sideBySide ? '1 1 0' : '0 0 auto',
            minWidth: 0,
            minHeight: 0,
            ...(sideBySide && { maxHeight: '100%', ...panelScrollSx }),
            display: 'grid',
            gridTemplateColumns: 'repeat(12, 1fr)',
            gridAutoRows: 'min-content',
            gap: 1.5,
            containerType: 'inline-size',
          }}
        >
          {mainSections.map((section) => renderSectionCards(section, true))}
          {overviewQuery.data.sections.length === 0 && (
            <Box sx={{ gridColumn: '1 / -1' }}>
              <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
                No items found
              </Typography>
            </Box>
          )}
        </Box>
      </Box>
      <EditItemDialog
        projectUid={projectUid}
        itemUid={editDialogItemUid}
        onClose={() => {
          setEditDialogItemUid(null)
          invalidateOverview()
        }}
      />
    </Box>
  )
}

interface OverviewSectionCardProps {
  group: OverviewSection
  allSchemas: Record<
    string,
    {
      attributes: Record<string, AttributeSchema>
      privateAttributes?: Record<string, AttributeSchema>
    }
  >
  targetAttributes: string[]
  section: OverviewSectionLayout
  siblingGroups: OverviewSection[]
  editedItems: Record<string, Record<string, Attribute<AttributeValueTypes>>>
  onAttributeUpdate: (
    targetItemUid: string,
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ) => void
  onAddChild: (parentItemUid: string, identifier: string) => void
  onCopyToParent: (itemUid: string, targetParentUid: string, identifier: string) => void
  onMoveAttribute: (
    sourceItemUid: string,
    attributeTag: string,
    targetItemUid: string,
  ) => void
  onMoveItem: (itemUid: string, targetParentUid: string) => void
  onDelete: (groupItemUid: string) => void
  isMutating: boolean
  /** Fill the height of the column, dividing it among the long texts inside. */
  fillHeight?: boolean
  /** How an identifier chip opens its item, and what it says instead when the
   * item has unsaved edits. Both undefined where nothing can be opened. */
  openItem?: (uid: string) => (() => void) | undefined
  openBlockedAction?: (uid: string) => ValueAction[] | undefined
  /** Shown in the docked panel right now, so its chip can say so. */
  openedItemUid?: string | null
}

const ATTRIBUTE_DRAG_MIME = 'application/x-overview-attribute'
/** A whole item, rather than one of its values. Its own MIME type so a card
 * can tell the two gestures apart while the drag is still in flight. */
const ITEM_DRAG_MIME = 'application/x-overview-item'

interface AttributeDragPayload {
  itemUid: string
  compoundTag: string
  /** The value belongs to the item itself, not to an item inside it, so it
   * swaps with the other item rather than with an observation in it. */
  parentAttribute: boolean
}

interface ItemDragPayload {
  itemUid: string
}

/**
 * Apply per-tag edits onto an item, deep-merging compound tags
 * (e.g. "statement.diagnose") into the parent ObjectAttribute's value rather
 * than dropping them as bogus top-level keys. When the parent ObjectAttribute
 * is missing — typical for freshly-created items whose schema-defined
 * attributes haven't been materialised yet — fall back to the schema to
 * synthesise an empty parent so the child edit isn't silently dropped.
 */
function applyEditsToItem<
  T extends {
    attributes: Record<string, Attribute<AttributeValueTypes>>
    privateAttributes: Record<string, Attribute<AttributeValueTypes>>
  },
>(
  item: T,
  edits: Record<string, Attribute<AttributeValueTypes>>,
  itemSchema?: {
    attributes: Record<string, AttributeSchema>
    privateAttributes?: Record<string, AttributeSchema>
  },
): T {
  const result: T = {
    ...item,
    attributes: { ...item.attributes },
    privateAttributes: { ...item.privateAttributes },
  }
  for (const [tag, editedAttr] of Object.entries(edits)) {
    const dotIndex = tag.indexOf('.')
    if (dotIndex < 0) {
      if (tag in result.privateAttributes) {
        result.privateAttributes[tag] = editedAttr
      } else {
        result.attributes[tag] = editedAttr
      }
      continue
    }
    const parentTag = tag.substring(0, dotIndex)
    const childTag = tag.substring(dotIndex + 1)
    let bucket: Record<string, Attribute<AttributeValueTypes>> | null =
      parentTag in result.attributes
        ? result.attributes
        : parentTag in result.privateAttributes
        ? result.privateAttributes
        : null
    if (!bucket) {
      const parentSchema =
        itemSchema?.attributes[parentTag] ?? itemSchema?.privateAttributes?.[parentTag]
      if (
        !parentSchema ||
        parentSchema.attributeValueType !== AttributeValueType.OBJECT
      ) {
        continue
      }
      bucket =
        itemSchema?.privateAttributes && parentTag in itemSchema.privateAttributes
          ? result.privateAttributes
          : result.attributes
      bucket[parentTag] = {
        uid: '00000000-0000-0000-0000-000000000000',
        displayValue: '',
        valid: parentSchema.optional,
        schemaUid: parentSchema.uid,
        attributeValueType: AttributeValueType.OBJECT,
        originalValue: null,
        updatedValue: null,
        mappedValue: null,
        mappableValue: null,
        mappingItemUid: null,
      }
    }
    const parent = bucket[parentTag]
    if (parent.attributeValueType !== AttributeValueType.OBJECT) continue
    const currentValue =
      (parent.updatedValue as Record<string, Attribute<AttributeValueTypes>> | null) ??
      (parent.mappedValue as Record<string, Attribute<AttributeValueTypes>> | null) ??
      (parent.originalValue as Record<string, Attribute<AttributeValueTypes>> | null) ??
      {}
    bucket[parentTag] = {
      ...parent,
      updatedValue: { ...currentValue, [childTag]: editedAttr },
    }
  }
  return result
}

function OverviewSectionCard({
  group,
  allSchemas,
  targetAttributes,
  section,
  siblingGroups,
  editedItems,
  onAttributeUpdate,
  onAddChild,
  onCopyToParent,
  onMoveAttribute,
  onMoveItem,
  onDelete,
  isMutating,
  fillHeight = false,
  openItem,
  openBlockedAction,
  openedItemUid,
}: OverviewSectionCardProps): ReactElement {
  const [confirmDelete, setConfirmDelete] = useState(false)
  const { pseudonymMode } = usePseudonym()
  const targetSchema = allSchemas[group.schemaUid]
  const displayLabel =
    group.pseudonym !== null
      ? getDisplayIdentifier(
          { uid: group.itemUid, identifier: group.label, pseudonym: group.pseudonym },
          pseudonymMode,
        )
      : group.label

  const [copyAnchor, setCopyAnchor] = useState<{
    el: HTMLElement
    itemUid: string
  } | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)
  const [addDialog, setAddDialog] = useState<{
    parentItemUid: string
    identifier: string
  } | null>(null)
  const [copyDialog, setCopyDialog] = useState<{
    itemUid: string
    targetParentUid: string
    targetLabel: string
    identifier: string
  } | null>(null)

  const submitAdd = (): void => {
    if (!addDialog) return
    const trimmed = addDialog.identifier.trim()
    if (!trimmed) return
    onAddChild(addDialog.parentItemUid, trimmed)
    setAddDialog(null)
  }

  const submitCopy = (): void => {
    if (!copyDialog) return
    const trimmed = copyDialog.identifier.trim()
    if (!trimmed) return
    onCopyToParent(copyDialog.itemUid, copyDialog.targetParentUid, trimmed)
    setCopyDialog(null)
  }

  const otherParents = useMemo(
    () => siblingGroups.filter((g) => g.itemUid !== group.itemUid),
    [siblingGroups, group.itemUid],
  )

  const ownItemUids = useMemo(
    () => new Set(group.items.map((i) => i.itemUid)),
    [group.items],
  )

  const handleCardDragOver = (e: React.DragEvent): void => {
    if (!section.reassignable) return
    if (
      !e.dataTransfer.types.includes(ATTRIBUTE_DRAG_MIME) &&
      !e.dataTransfer.types.includes(ITEM_DRAG_MIME)
    ) {
      return
    }
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setIsDragOver(true)
  }

  const handleCardDragLeave = (e: React.DragEvent): void => {
    if (!e.currentTarget.contains(e.relatedTarget as Node)) {
      setIsDragOver(false)
    }
  }

  const handleCardDrop = (e: React.DragEvent): void => {
    if (!section.reassignable) return
    setIsDragOver(false)

    // A whole item: it moves here, keeping everything on it.
    const itemRaw = e.dataTransfer.getData(ITEM_DRAG_MIME)
    if (itemRaw) {
      let itemPayload: ItemDragPayload
      try {
        itemPayload = JSON.parse(itemRaw) as ItemDragPayload
      } catch {
        return
      }
      if (ownItemUids.has(itemPayload.itemUid)) return
      e.preventDefault()
      onMoveItem(itemPayload.itemUid, group.itemUid)
      return
    }

    const raw = e.dataTransfer.getData(ATTRIBUTE_DRAG_MIME)
    if (!raw) return
    let payload: AttributeDragPayload
    try {
      payload = JSON.parse(raw) as AttributeDragPayload
    } catch {
      return
    }

    // A value of the item itself swaps with the same value on this item; a value
    // of an item inside it swaps with the matching item here. Both sides always
    // exist for the first, which is why only the second can come up short.
    const targetItemUid = payload.parentAttribute
      ? group.parentItem?.itemUid
      : group.items[0]?.itemUid
    if (targetItemUid === undefined) return
    // Same item: nothing to swap with.
    if (targetItemUid === payload.itemUid || ownItemUids.has(payload.itemUid)) return
    e.preventDefault()
    onMoveAttribute(payload.itemUid, payload.compoundTag, targetItemUid)
  }

  return (
    <Card
      variant="outlined"
      onDragOver={handleCardDragOver}
      onDragLeave={handleCardDragLeave}
      onDrop={handleCardDrop}
      sx={{
        outline: isDragOver ? '2px dashed' : 'none',
        outlineColor: 'primary.main',
        transition: 'outline-color 0.15s ease',
        // A column, so the height reaches the attributes that divide it.
        ...(fillHeight && {
          height: '100%',
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
        }),
      }}
    >
      {/* Tighter than the default card padding: several items are read at once,
          so chrome around each one costs more than it gives. */}
      <CardContent
        sx={{
          p: 1,
          '&:last-child': { pb: 1 },
          ...(fillHeight && {
            flex: 1,
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
          }),
        }}
      >
        <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
          <ValueActions
            value={displayLabel}
            monospace
            copyable
            copyLabel="Copy identifier"
            onOpen={openItem?.(group.itemUid)}
            actions={openBlockedAction?.(group.itemUid)}
          />
          <Box sx={{ flexGrow: 1 }} />
          {section.creatable && (
            <Tooltip title={group.items.length > 0 ? 'Already has an entry' : 'Add'}>
              <span>
                <IconButton
                  size="small"
                  onClick={() =>
                    setAddDialog({
                      parentItemUid: group.itemUid,
                      identifier: '',
                    })
                  }
                  disabled={isMutating || group.items.length > 0}
                >
                  <Add fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          )}
          {section.deletable && (
            <Tooltip title={`Remove ${displayLabel} from the project`}>
              <span>
                <IconButton
                  size="small"
                  color="error"
                  onClick={() => setConfirmDelete(true)}
                  disabled={isMutating}
                >
                  <Delete fontSize="small" />
                </IconButton>
              </span>
            </Tooltip>
          )}
        </Stack>
        <Stack
          spacing={0.5}
          sx={{ mt: 0.5, ...(fillHeight && { flex: 1, minHeight: 0 }) }}
        >
          {/* The group's own attributes, above the items grouped under it: a
              specimen's anatomical site belongs with that specimen's
              diagnoses, not in a section of its own. */}
          {group.parentItem !== null && group.parentSchemaUid !== null && (
            <OverviewItemRow
              key={group.parentItem.itemUid}
              targetItem={group.parentItem}
              targetSchema={allSchemas[group.parentSchemaUid]}
              targetAttributes={section.parentAttributes}
              editedAttributes={editedItems[group.parentItem.itemUid]}
              onAttributeUpdate={onAttributeUpdate}
              draggableAttributes={
                section.reassignable ? section.reassignableAttributes : undefined
              }
              parentAttributes
              fillHeight={fillHeight}
            />
          )}
          {group.items.map((targetItem) => (
            <OverviewItemRow
              key={targetItem.itemUid}
              targetItem={targetItem}
              targetSchema={targetSchema}
              targetAttributes={targetAttributes}
              defaultCollapsed={section.defaultCollapsed}
              editedAttributes={editedItems[targetItem.itemUid]}
              onAttributeUpdate={onAttributeUpdate}
              draggableAttributes={
                section.reassignable ? section.reassignableAttributes : undefined
              }
              draggableItem={section.reassignable}
              fillHeight={fillHeight}
              actions={
                <React.Fragment>
                  {/* An icon rather than an identifier chip: the card already
                      says which item this belongs to, and a second identifier
                      per row costs most of the width of a narrow card. */}
                  {openItem !== undefined && (
                    <Tooltip
                      title={
                        openItem(targetItem.itemUid) !== undefined
                          ? 'Open'
                          : 'Save the changes to this item before opening it'
                      }
                    >
                      <span>
                        <IconButton
                          size="small"
                          onClick={openItem(targetItem.itemUid)}
                          disabled={openItem(targetItem.itemUid) === undefined}
                          color={
                            targetItem.itemUid === openedItemUid ? 'primary' : 'default'
                          }
                        >
                          <ChevronRight fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  )}
                  {section.copyable && otherParents.length > 0 && (
                    <Tooltip title="Copy to another item…">
                      <span>
                        <IconButton
                          size="small"
                          onClick={(e) =>
                            setCopyAnchor({
                              el: e.currentTarget,
                              itemUid: targetItem.itemUid,
                            })
                          }
                          disabled={isMutating}
                        >
                          <FileCopy fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  )}
                </React.Fragment>
              }
            />
          ))}
        </Stack>
      </CardContent>
      <Menu
        anchorEl={copyAnchor?.el}
        open={Boolean(copyAnchor)}
        onClose={() => setCopyAnchor(null)}
      >
        {otherParents.map((sibling) => (
          <MenuItem
            key={sibling.itemUid}
            onClick={() => {
              if (copyAnchor) {
                const source = group.items.find((i) => i.itemUid === copyAnchor.itemUid)
                setCopyDialog({
                  itemUid: copyAnchor.itemUid,
                  targetParentUid: sibling.itemUid,
                  targetLabel: sibling.label,
                  identifier: source ? `${source.identifier} (copy)` : '',
                })
              }
              setCopyAnchor(null)
            }}
          >
            {sibling.label}
          </MenuItem>
        ))}
      </Menu>
      <Dialog
        open={Boolean(addDialog)}
        onClose={() => setAddDialog(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>New {section.displayName}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Identifier"
            fullWidth
            value={addDialog?.identifier ?? ''}
            onChange={(e) =>
              setAddDialog((prev) =>
                prev ? { ...prev, identifier: e.target.value } : prev,
              )
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                submitAdd()
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialog(null)}>Cancel</Button>
          <Button
            onClick={submitAdd}
            disabled={!addDialog?.identifier.trim() || isMutating}
            variant="contained"
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={Boolean(copyDialog)}
        onClose={() => setCopyDialog(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Copy to {copyDialog?.targetLabel}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="Identifier"
            fullWidth
            value={copyDialog?.identifier ?? ''}
            onChange={(e) =>
              setCopyDialog((prev) =>
                prev ? { ...prev, identifier: e.target.value } : prev,
              )
            }
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                submitCopy()
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCopyDialog(null)}>Cancel</Button>
          <Button
            onClick={submitCopy}
            disabled={!copyDialog?.identifier.trim() || isMutating}
            variant="contained"
          >
            Copy
          </Button>
        </DialogActions>
      </Dialog>
      <Dialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Remove {displayLabel}?</DialogTitle>
        <DialogContent>
          <Typography>
            This removes {displayLabel} and its blocks, slides, images and
            observations from the project.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDelete(false)}>Cancel</Button>
          <Button
            onClick={() => {
              onDelete(group.itemUid)
              setConfirmDelete(false)
            }}
            disabled={isMutating}
            color="error"
            variant="contained"
          >
            Remove
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  )
}

interface OverviewItemRowProps {
  targetItem: OverviewItem
  targetSchema:
    | {
        attributes: Record<string, AttributeSchema>
        privateAttributes?: Record<string, AttributeSchema>
      }
    | undefined
  targetAttributes: string[]
  defaultCollapsed?: string[]
  editedAttributes?: Record<string, Attribute<AttributeValueTypes>>
  onAttributeUpdate: (
    targetItemUid: string,
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ) => void
  /** Compound tags that get their own drag handle, putting an
   * AttributeDragPayload on the dataTransfer. Empty means all of them. */
  draggableAttributes?: string[]
  /** These attributes belong to the item itself, so they swap with the other
   * item rather than with an item inside it. */
  parentAttributes?: boolean
  /** The row gets a handle of its own, dragging the whole item to another item
   * rather than one of its values. */
  draggableItem?: boolean
  /** Long texts in the row divide the height it is given. */
  fillHeight?: boolean
  actions?: ReactElement | null
}

/**
 * Extract nested schemas and layout from a target schema for compound tags.
 * E.g. for tags like "statement.diagnose", finds the "statement" ObjectAttributeSchema
 * and returns its nested schemas and layout.
 */
function resolveNestedSchemasAndLayout(
  targetSchema:
    | {
        attributes: Record<string, AttributeSchema>
        privateAttributes?: Record<string, AttributeSchema>
      }
    | undefined,
  targetAttributes: string[],
): { schemas: Record<string, AttributeSchema>; layout: AttributeGroupLayout[] } {
  if (!targetSchema) return { schemas: {}, layout: [] }

  const allAttrs = {
    ...targetSchema.attributes,
    ...(targetSchema.privateAttributes ?? {}),
  }

  const schemas: Record<string, AttributeSchema> = {}
  let layout: AttributeGroupLayout[] = []
  const targetTagSet = new Set<string>()

  for (const compoundTag of targetAttributes) {
    const dotIndex = compoundTag.indexOf('.')
    if (dotIndex > 0) {
      const parentTag = compoundTag.substring(0, dotIndex)
      const childTag = compoundTag.substring(dotIndex + 1)
      const parentSchema = allAttrs[parentTag]
      if (parentSchema && 'attributes' in parentSchema) {
        const objSchema = parentSchema as ObjectAttributeSchema
        const childSchema = objSchema.attributes[childTag]
        if (childSchema) {
          schemas[childTag] = childSchema
          targetTagSet.add(childTag)
        }
        if (objSchema.attributeLayout?.length > 0) {
          layout = objSchema.attributeLayout
        }
      }
    } else {
      const schema = allAttrs[compoundTag]
      if (schema) {
        schemas[compoundTag] = schema
        targetTagSet.add(compoundTag)
      }
    }
  }

  // Filter layout to only include sections that have target attributes
  if (layout.length > 0) {
    layout = layout
      .map((group) => ({
        ...group,
        attributes: Object.fromEntries(
          Object.entries(group.attributes).filter(([tag]) => targetTagSet.has(tag)),
        ),
      }))
      .filter((group) => Object.keys(group.attributes).length > 0)
  }

  return { schemas, layout }
}

function OverviewItemRow({
  targetItem,
  targetSchema,
  targetAttributes,
  defaultCollapsed,
  editedAttributes,
  onAttributeUpdate,
  draggableAttributes,
  parentAttributes = false,
  draggableItem = false,
  fillHeight = false,
  actions,
}: OverviewItemRowProps): ReactElement {
  // Combine all item attributes for lookup
  const allItemAttributes = useMemo(
    () => ({ ...targetItem.attributes, ...targetItem.privateAttributes }),
    [targetItem.attributes, targetItem.privateAttributes],
  )

  // When targetAttributes is empty, show all attributes from the data
  const effectiveAttributes = useMemo(
    () =>
      targetAttributes.length > 0 ? targetAttributes : Object.keys(allItemAttributes),
    [targetAttributes, allItemAttributes],
  )

  const { schemas, layout } = useMemo(
    () => resolveNestedSchemasAndLayout(targetSchema, effectiveAttributes),
    [targetSchema, effectiveAttributes],
  )

  // Build attributes dict using child tags, merging edits and API data
  const mergedAttributes = useMemo(() => {
    const result: Record<string, Attribute<AttributeValueTypes>> = {}
    for (const compoundTag of effectiveAttributes) {
      const dotIndex = compoundTag.indexOf('.')
      const childTag = dotIndex > 0 ? compoundTag.substring(dotIndex + 1) : compoundTag
      const attr = editedAttributes?.[compoundTag] ?? allItemAttributes[compoundTag]
      if (attr) {
        result[childTag] = attr
      }
    }
    return result
  }, [effectiveAttributes, editedAttributes, allItemAttributes])

  // Map child tag back to compound tag for updates.
  // Note: if two compound tags share the same child tag (e.g. "a.value" and "b.value"),
  // the last one wins. This is acceptable as long as sections target a single parent.
  const childToCompoundTag = useMemo(() => {
    const map: Record<string, string> = {}
    for (const compoundTag of effectiveAttributes) {
      const dotIndex = compoundTag.indexOf('.')
      const childTag = dotIndex > 0 ? compoundTag.substring(dotIndex + 1) : compoundTag
      map[childTag] = compoundTag
    }
    return map
  }, [effectiveAttributes])

  // Translate the section-level default-collapsed list (which uses the
  // section's compound tags) into the child tags that AttributeDetails sees.
  const childDefaultCollapsed = useMemo(() => {
    if (!defaultCollapsed || defaultCollapsed.length === 0) return undefined
    return defaultCollapsed.map((compoundTag) => {
      const dotIndex = compoundTag.indexOf('.')
      return dotIndex > 0 ? compoundTag.substring(dotIndex + 1) : compoundTag
    })
  }, [defaultCollapsed])

  const renderAttributeContent = draggableAttributes
    ? (childTag: string, content: ReactElement): ReactElement => {
        const compoundTag = childToCompoundTag[childTag] ?? childTag
        // Only the attributes the section names, so the handle appears on the
        // values worth moving on their own rather than on every field.
        if (
          draggableAttributes.length > 0 &&
          !draggableAttributes.includes(compoundTag)
        ) {
          return content
        }
        const payload: AttributeDragPayload = {
          itemUid: targetItem.itemUid,
          compoundTag,
          parentAttribute: parentAttributes,
        }
        return (
          <Stack direction="row" spacing={0.5} sx={{ alignItems: 'flex-start' }}>
            <Tooltip title="Drag to swap this value with another item">
              <Box
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData(ATTRIBUTE_DRAG_MIME, JSON.stringify(payload))
                  e.dataTransfer.effectAllowed = 'move'
                }}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  cursor: 'grab',
                  userSelect: 'none',
                  color: 'action.active',
                  pt: 0.5,
                  '&:active': { cursor: 'grabbing' },
                }}
              >
                <DragIndicator fontSize="small" />
              </Box>
            </Tooltip>
            <Box sx={{ flexGrow: 1, minWidth: 0 }}>{content}</Box>
          </Stack>
        )
      }
    : undefined

  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{
        alignItems: 'flex-start',
        p: 0.75,
        borderRadius: 1,
        bgcolor: 'action.hover',
        // Stretched, not top-aligned: the attributes inside share the height of
        // the row, and a row whose children do not stretch has no height to
        // give them.
        ...(fillHeight && { flex: 1, minHeight: 0, alignItems: 'stretch' }),
      }}
    >
      {/* Grabbing the row takes the whole item to another item; the handles on
          individual values swap just that value. */}
      {draggableItem && (
        <Tooltip title="Drag to move this whole entry to another item">
          <Box
            draggable
            onDragStart={(event) => {
              const payload: ItemDragPayload = { itemUid: targetItem.itemUid }
              event.dataTransfer.setData(ITEM_DRAG_MIME, JSON.stringify(payload))
              event.dataTransfer.effectAllowed = 'move'
            }}
            sx={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'grab',
              userSelect: 'none',
              color: 'text.secondary',
              pt: 0.5,
              '&:active': { cursor: 'grabbing' },
            }}
          >
            <DragHandle fontSize="small" />
          </Box>
        </Tooltip>
      )}
      <Box sx={{ flexGrow: 1, minWidth: 0, ...(fillHeight && { minHeight: 0 }) }}>
        <AttributeDetails
          schemas={schemas}
          attributes={mergedAttributes}
          action={ItemDetailAction.EDIT}
          attributeLayout={layout}
          defaultCollapsed={childDefaultCollapsed}
          // Enough that the outlined fields do not touch: their labels sit on
          // the top border, and the value control floats just above it.
          spacing={1.5}
          handleAttributeOpen={() => {}}
          handleAttributeUpdate={(childTag, attr) => {
            const compoundTag = childToCompoundTag[childTag] ?? childTag
            onAttributeUpdate(targetItem.itemUid, compoundTag, attr)
          }}
          renderAttributeContent={renderAttributeContent}
          // The value picker is for scrutinising a mapping, which is not what
          // this view is for, and it does not fit the item cards.
          showValueControls={false}
          fillHeight={fillHeight}
        />
      </Box>
      {actions && <Box sx={{ flexShrink: 0 }}>{actions}</Box>}
    </Stack>
  )
}
