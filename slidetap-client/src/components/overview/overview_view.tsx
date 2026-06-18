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
  Chip,
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
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactElement } from 'react'
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
  Breakpoint,
  ObjectAttributeSchema,
} from 'src/models/schema/attribute_schema'
import type {
  OverviewLayout,
  OverviewSectionLayout,
} from 'src/models/schema/overview_layout'
import type { TableRequest } from 'src/models/table_item'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'

const containerBreakpoints: Record<string, number> = {
  sm: 400,
  md: 600,
  lg: 800,
  xl: 1024,
}

const getSectionSx = (
  width: Partial<Record<Breakpoint, number>>,
  expand: boolean,
): Record<string, any> => {
  if (expand) {
    return { gridColumn: '1 / -1' }
  }
  const sx: Record<string, any> = {
    gridColumn: `span ${width.xs ?? 12}`,
  }
  for (const [bp, span] of Object.entries(width)) {
    if (bp === 'xs') continue
    const minWidth = containerBreakpoints[bp]
    if (minWidth !== undefined) {
      sx[`@container (min-width: ${minWidth}px)`] = {
        gridColumn: `span ${span}`,
      }
    }
  }
  return sx
}

interface OverviewViewProps {
  projectUid: string
  itemUid: string
  overviewLayout: OverviewLayout
  batchUid?: string
  tableRequest?: TableRequest
}

export default function OverviewView({
  projectUid,
  itemUid,
  overviewLayout,
  batchUid,
  tableRequest,
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
      target,
    }: {
      sourceItemUid: string
      attributeTag: string
      target: { itemUid: string } | { parentUid: string }
    }) => await itemApi.moveAttribute(sourceItemUid, attributeTag, target),
    onSuccess: (response) => {
      invalidateOverview()
      if (response?.createdItemUid) {
        setEditDialogItemUid(response.createdItemUid)
      }
    },
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
  }, [navigatePrevious, navigateNext, handleSaveAll, saveItemMutation.isPending])

  if (overviewQuery.isLoading) {
    return <LinearProgress />
  }

  if (!overviewQuery.data) {
    return <Typography>No data available</Typography>
  }

  const isDirty = Object.keys(editedItems).length > 0

  return (
    <Box sx={{ height: '100%' }}>
      {/* Navigation header — full width */}
      <Card sx={{ mb: 2 }}>
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
          <Typography variant="h6" sx={{ flex: 1, textAlign: 'center' }}>
            {getDisplayIdentifier(
              {
                uid: overviewQuery.data.itemUid,
                identifier: overviewQuery.data.identifier,
                pseudonym: overviewQuery.data.pseudonym,
              },
              pseudonymMode,
            )}
          </Typography>
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

      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(12, 1fr)',
          gap: 2,
          containerType: 'inline-size',
        }}
      >
        {overviewLayout.sections.map((section) => {
          const sectionData = overviewQuery.data.sections.filter(
            (g) => g.schemaUid === section.schemaUid,
          )
          if (sectionData.length === 0) return null

          const sectionSx = getSectionSx(section.width, section.expand)

          return sectionData.map((group) => (
            <Box key={group.itemUid} sx={sectionSx}>
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
                  copyToParentMutation.mutate({
                    itemUid,
                    targetParentUid,
                    identifier,
                  })
                }
                onMoveAttribute={(sourceItemUid, attributeTag, target) => {
                  moveAttributeMutation.mutate({
                    sourceItemUid,
                    attributeTag,
                    target,
                  })
                }}
                onDelete={(groupItemUid) =>
                  deleteGroupMutation.mutate({ itemUid: groupItemUid })
                }
                isMutating={
                  addChildMutation.isPending ||
                  copyToParentMutation.isPending ||
                  moveAttributeMutation.isPending ||
                  deleteGroupMutation.isPending
                }
              />
            </Box>
          ))
        })}
        {overviewQuery.data.sections.length === 0 && (
          <Box sx={{ gridColumn: '1 / -1' }}>
            <Typography color="text.secondary" sx={{ textAlign: 'center', py: 4 }}>
              No items found
            </Typography>
          </Box>
        )}
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
    target: { itemUid: string } | { parentUid: string },
  ) => void
  onDelete: (groupItemUid: string) => void
  isMutating: boolean
}

const ATTRIBUTE_DRAG_MIME = 'application/x-overview-attribute'

interface AttributeDragPayload {
  itemUid: string
  compoundTag: string
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
  onDelete,
  isMutating,
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
    if (!e.dataTransfer.types.includes(ATTRIBUTE_DRAG_MIME)) return
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
    const raw = e.dataTransfer.getData(ATTRIBUTE_DRAG_MIME)
    if (!raw) return
    let payload: AttributeDragPayload
    try {
      payload = JSON.parse(raw) as AttributeDragPayload
    } catch {
      return
    }
    // Ignore drops from items already in this group — same-group
    // attribute moves are no-ops.
    if (ownItemUids.has(payload.itemUid)) return
    e.preventDefault()
    // If the group already has an item with the section's schema, swap with
    // it directly. Otherwise let the backend create a new child of this
    // group's parent in the same transaction.
    const existing = group.items[0]
    const target = existing
      ? { itemUid: existing.itemUid }
      : { parentUid: group.itemUid }
    onMoveAttribute(payload.itemUid, payload.compoundTag, target)
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
      }}
    >
      <CardContent>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Chip label={displayLabel} color="primary" size="small" variant="outlined" />
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
        <Stack spacing={1} sx={{ mt: 1 }}>
          {group.items.map((targetItem) => (
            <OverviewItemRow
              key={targetItem.itemUid}
              targetItem={targetItem}
              targetSchema={targetSchema}
              targetAttributes={targetAttributes}
              defaultCollapsed={section.defaultCollapsed}
              editedAttributes={editedItems[targetItem.itemUid]}
              onAttributeUpdate={onAttributeUpdate}
              draggableAttributes={section.reassignable}
              actions={
                section.copyable && otherParents.length > 0 ? (
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
                ) : null
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
  /** When true, each rendered attribute gets its own drag handle that puts
   * an AttributeDragPayload on the dataTransfer. */
  draggableAttributes?: boolean
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
        const payload: AttributeDragPayload = {
          itemUid: targetItem.itemUid,
          compoundTag,
        }
        return (
          <Stack direction="row" alignItems="flex-start" spacing={0.5}>
            <Tooltip title="Drag to move/swap with another item">
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
      alignItems="flex-start"
      spacing={1}
      sx={{ p: 1, borderRadius: 1, bgcolor: 'action.hover' }}
    >
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <AttributeDetails
          schemas={schemas}
          attributes={mergedAttributes}
          action={ItemDetailAction.EDIT}
          attributeLayout={layout}
          defaultCollapsed={childDefaultCollapsed}
          spacing={1}
          handleAttributeOpen={() => {}}
          handleAttributeUpdate={(childTag, attr) => {
            const compoundTag = childToCompoundTag[childTag] ?? childTag
            onAttributeUpdate(targetItem.itemUid, compoundTag, attr)
          }}
          renderAttributeContent={renderAttributeContent}
        />
      </Box>
      {actions && <Box sx={{ flexShrink: 0 }}>{actions}</Box>}
    </Stack>
  )
}
