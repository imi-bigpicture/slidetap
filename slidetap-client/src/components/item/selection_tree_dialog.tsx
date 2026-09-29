//    Copyright 2026 SECTRA AB
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

import { ChevronRight, ExpandMore } from '@mui/icons-material'
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  LinearProgress,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
} from '@mui/material'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState, type ReactElement } from 'react'
import OutlinedFormControl from 'src/components/attribute/outlined_form_control'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import type { SelectionTree, SelectionTreeNode } from 'src/models/item_select'
import type { RootSchema } from 'src/models/schema/root_schema'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'
import DisplayItemTags from './display_item_tags'
import { ChangeGroup, schemaName } from './selection_preview'

/** The items asked for, as the parent of the top of each tree. Always in. */
const ROOT = ''

/** A row as it is drawn: a node at a place in a tree. An item under several
 * others is drawn under each, and is one item for choosing. */
interface Row {
  node: SelectionTreeNode
  path: string
  depth: number
}

/** How the nodes of every tree hang together, by uid. */
interface TreeIndex {
  nodes: Map<string, SelectionTreeNode>
  parents: Map<string, Set<string>>
}

function indexTrees(trees: SelectionTree[]): TreeIndex {
  const nodes = new Map<string, SelectionTreeNode>()
  const parents = new Map<string, Set<string>>()
  const visit = (node: SelectionTreeNode, parent: string): void => {
    nodes.set(node.uid, node)
    const nodeParents = parents.get(node.uid) ?? new Set<string>()
    nodeParents.add(parent)
    parents.set(node.uid, nodeParents)
    node.children.forEach((child) => visit(child, node.uid))
  }
  trees.forEach((tree) => {
    tree.up.forEach((node) => visit(node, ROOT))
    tree.down.forEach((node) => visit(node, ROOT))
  })
  return { nodes, parents }
}

function defaultsOf(index: TreeIndex): Set<string> {
  return new Set(
    [...index.nodes.values()]
      .filter((node) => node.default && node.selectable)
      .map((node) => node.uid),
  )
}

/** Which nodes are chosen: ticked, allowed, and with every parent above them
 * in the tree chosen too. A child cannot go without what it belongs to. */
function chosenOf(index: TreeIndex, ticked: Set<string>): Set<string> {
  const memo = new Map<string, boolean>()
  const chosen = (uid: string): boolean => {
    if (uid === ROOT) {
      return true
    }
    const known = memo.get(uid)
    if (known !== undefined) {
      return known
    }
    // Guarded against a relation leading back, which the server already cuts.
    memo.set(uid, false)
    const node = index.nodes.get(uid)
    const result =
      node !== undefined &&
      node.selectable &&
      ticked.has(uid) &&
      [...(index.parents.get(uid) ?? [])].every(chosen)
    memo.set(uid, result)
    return result
  }
  return new Set([...index.nodes.keys()].filter(chosen))
}

/** Every row of a set of top-level nodes, depth first. */
function rowsOf(nodes: SelectionTreeNode[], prefix: string, depth: number): Row[] {
  return nodes.flatMap((node) => {
    const path = `${prefix}/${node.uid}`
    return [{ node, path, depth }, ...rowsOf(node.children, path, depth + 1)]
  })
}

/** The shallowest depth where not every row is chosen, if there is one. */
function firstMixedDepth(rows: Row[], chosen: Set<string>): number | undefined {
  const depths = [...new Set(rows.map((row) => row.depth))].sort(
    (first, second) => first - second,
  )
  return depths.find((depth) =>
    rows.some((row) => row.depth === depth && !chosen.has(row.node.uid)),
  )
}

/** What starts open: every row with children above the first depth where
 * not everything is chosen, so the first level with something left out is
 * in view and what is below it is not. Where everything is chosen, nothing
 * is open. */
function openAtStart(rows: Row[], chosen: Set<string>): string[] {
  const firstMixed = firstMixedDepth(rows, chosen)
  if (firstMixed === undefined) {
    return []
  }
  return rows
    .filter((row) => row.depth < firstMixed && row.node.children.length > 0)
    .map((row) => row.path)
}

interface TreeRowProps {
  node: SelectionTreeNode
  path: string
  depth: number
  index: TreeIndex
  chosen: Set<string>
  expanded: Set<string>
  onToggle: (uid: string, checked: boolean) => void
  onExpand: (path: string) => void
}

function TreeRow({
  node,
  path,
  depth,
  index,
  chosen,
  expanded,
  onToggle,
  onExpand,
}: TreeRowProps): ReactElement {
  const schema = useSchemaContext()
  const parentsChosen = [...(index.parents.get(node.uid) ?? [])].every(
    (parent) => parent === ROOT || chosen.has(parent),
  )
  const enabled = node.selectable && parentsChosen
  const open = expanded.has(path)
  const hasChildren = node.children.length > 0
  const reason = node.locked
    ? 'Its batch is locked'
    : !node.selectable
      ? 'Still holds other items, which would go with it'
      : !parentsChosen
        ? 'Choose what it belongs to first'
        : ''
  return (
    <>
      <Stack
        direction="row"
        spacing={0.5}
        sx={{ alignItems: 'center', pl: depth * 2.5, minHeight: 32 }}
      >
        <IconButton
          size="small"
          onClick={() => onExpand(path)}
          sx={{ visibility: hasChildren ? 'visible' : 'hidden' }}
        >
          {open ? <ExpandMore fontSize="small" /> : <ChevronRight fontSize="small" />}
        </IconButton>
        <Tooltip title={reason}>
          <span>
            <Checkbox
              size="small"
              checked={chosen.has(node.uid)}
              disabled={!enabled}
              onChange={(event) => onToggle(node.uid, event.target.checked)}
              sx={{ p: 0.5 }}
            />
          </span>
        </Tooltip>
        <Typography variant="body2" noWrap>
          {schemaName(schema, node.schemaUid)} {node.identifier}
        </Typography>
        {hasChildren && !open && (
          <Typography variant="caption" color="text.secondary">
            ({node.children.length})
          </Typography>
        )}
        {node.curatorExcluded && (
          <Chip
            size="small"
            color="warning"
            variant="outlined"
            label="removed by hand"
          />
        )}
        {node.locked && <Chip size="small" variant="outlined" label="locked" />}
      </Stack>
      {node.withIt.length > 0 && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: 'block', pl: depth * 2.5 + 9 }}
        >
          With it:{' '}
          {node.withIt
            .map(
              (other) => `${schemaName(schema, other.schemaUid)} ${other.identifier}`,
            )
            .join(', ')}
        </Typography>
      )}
      {open &&
        node.children.map((child) => (
          <TreeRow
            key={child.uid}
            node={child}
            path={`${path}/${child.uid}`}
            depth={depth + 1}
            index={index}
            chosen={chosen}
            expanded={expanded}
            onToggle={onToggle}
            onExpand={onExpand}
          />
        ))}
    </>
  )
}

/** A kind of item, and the kinds found under it in one direction. */
interface SchemaNode {
  schemaUid: string
  /** Every item of this kind in the trees, wherever it sits; undefined while
   * the trees are still being worked out. */
  uids: string[] | undefined
  children: SchemaNode[]
}

/** The kinds one step below a kind in the schema: child samples, images and
 * observations of a sample, annotations and observations of an image, and
 * observations of an annotation. */
function kindsBelow(root: RootSchema, schemaUid: string): string[] {
  const sample = root.samples[schemaUid]
  if (sample !== undefined) {
    return [
      ...sample.children.map((relation) => relation.childUid),
      ...sample.images.map((relation) => relation.imageUid),
      ...sample.observations.map((relation) => relation.observationUid),
    ]
  }
  const image = root.images[schemaUid]
  if (image !== undefined) {
    return [
      ...image.annotations.map((relation) => relation.annotationUid),
      ...image.observations.map((relation) => relation.observationUid),
    ]
  }
  const annotation = root.annotations[schemaUid]
  if (annotation !== undefined) {
    return annotation.observations.map((relation) => relation.observationUid)
  }
  return []
}

/** The kinds one step above a kind in the schema: what it belongs to. */
function kindsAbove(root: RootSchema, schemaUid: string): string[] {
  const sample = root.samples[schemaUid]
  if (sample !== undefined) {
    return sample.parents.map((relation) => relation.parentUid)
  }
  const image = root.images[schemaUid]
  if (image !== undefined) {
    return image.samples.map((relation) => relation.sampleUid)
  }
  const annotation = root.annotations[schemaUid]
  if (annotation !== undefined) {
    return annotation.images.map((relation) => relation.imageUid)
  }
  const observation = root.observations[schemaUid]
  if (observation !== undefined) {
    return [
      ...observation.samples.map((relation) => relation.sampleUid),
      ...observation.images.map((relation) => relation.imageUid),
      ...observation.annotations.map((relation) => relation.annotationUid),
    ]
  }
  return []
}

/** Kinds, less any that is also further along under another of them, as
 * the server does for items: a specimen kind related to its being directly
 * and through its case is shown under the case only. */
function withoutKindShortcuts(nodes: SchemaNode[]): SchemaNode[] {
  const kindsIn = (node: SchemaNode): Set<string> =>
    new Set(node.children.flatMap((child) => [child.schemaUid, ...kindsIn(child)]))
  const further = nodes.map(kindsIn)
  return nodes.filter(
    (node, position) =>
      !further.some(
        (kinds, otherPosition) =>
          otherPosition !== position && kinds.has(node.schemaUid),
      ),
  )
}

/** The kinds above or below the items asked for, read off the schema alone,
 * so the tree is there before anything is counted. */
function kindTreeOf(
  root: RootSchema,
  startSchemas: string[],
  upward: boolean,
): SchemaNode[] {
  const next = upward ? kindsAbove : kindsBelow
  const build = (schemaUid: string, path: Set<string>): SchemaNode => ({
    schemaUid,
    uids: undefined,
    children: withoutKindShortcuts(
      [...new Set(next(root, schemaUid))]
        .filter((child) => !path.has(child))
        .map((child) => build(child, new Set([...path, child]))),
    ),
  })
  const start = new Set(startSchemas)
  const top = [...new Set(startSchemas.flatMap((schemaUid) => next(root, schemaUid)))]
    .filter((schemaUid) => !start.has(schemaUid))
    .map((schemaUid) => build(schemaUid, new Set([...start, schemaUid])))
  return withoutKindShortcuts(top)
}

/** The kind tree with what the trees hold of each kind, less the kinds that
 * hold nothing, and nothing below them does either. */
function countKinds(
  nodes: SchemaNode[],
  uidsByKind: Map<string, string[]>,
): SchemaNode[] {
  return nodes
    .map((node) => ({
      ...node,
      uids: uidsByKind.get(node.schemaUid) ?? [],
      children: countKinds(node.children, uidsByKind),
    }))
    .filter((node) => node.uids.length > 0 || node.children.length > 0)
}

/** Every node of a set of trees, by kind. */
function uidsByKindOf(topNodes: SelectionTreeNode[]): Map<string, string[]> {
  const found = new Map<string, Set<string>>()
  const visit = (node: SelectionTreeNode): void => {
    const uids = found.get(node.schemaUid) ?? new Set<string>()
    uids.add(node.uid)
    found.set(node.schemaUid, uids)
    node.children.forEach(visit)
  }
  topNodes.forEach(visit)
  return new Map([...found].map(([schemaUid, uids]) => [schemaUid, [...uids]]))
}

/** A choice made for a kind before the trees arrived, by direction and kind:
 * ticked or not. Applied to every item of the kind once they do. */
type KindChoices = Map<string, boolean>

function kindKey(upward: boolean, schemaUid: string): string {
  return `${upward ? 'up' : 'down'}/${schemaUid}`
}

function SchemaRow({
  node,
  depth,
  upward,
  index,
  chosen,
  kindChoices,
  aboveLeftOut = false,
  onToggleMany,
  onToggleKind,
}: {
  node: SchemaNode
  depth: number
  upward: boolean
  /** Undefined while the trees are still being worked out. */
  index: TreeIndex | undefined
  chosen: Set<string>
  kindChoices: KindChoices
  /** A kind above this one has been left out before the trees arrived. */
  aboveLeftOut?: boolean
  onToggleMany: (uids: string[], checked: boolean) => void
  onToggleKind: (upward: boolean, schemaUid: string, checked: boolean) => void
}): ReactElement {
  const schema = useSchemaContext()
  const uids = node.uids ?? []
  const loading = node.uids === undefined || index === undefined
  const count = uids.filter((uid) => chosen.has(uid)).length
  const kindChoice = kindChoices.get(kindKey(upward, node.schemaUid))
  // Before the trees arrive, a kind can be chosen for unless a kind above it
  // has been left out. After, it is choosable where any item of it is:
  // allowed, and with what it belongs to chosen.
  const enabled = loading
    ? !aboveLeftOut
    : uids.some((uid) => {
        const item = index.nodes.get(uid)
        return (
          item !== undefined &&
          item.selectable &&
          [...(index.parents.get(uid) ?? [])].every(
            (parent) => parent === ROOT || chosen.has(parent),
          )
        )
      })
  const leftOut = aboveLeftOut || (loading && kindChoice === false)
  return (
    <>
      <Stack
        direction="row"
        spacing={0.5}
        sx={{ alignItems: 'center', pl: depth * 2.5 + 1, minHeight: 32 }}
      >
        <Tooltip title={enabled ? '' : 'Choose what it belongs to first'}>
          <span>
            <Checkbox
              size="small"
              checked={
                loading
                  ? kindChoice === true && !aboveLeftOut
                  : count > 0 && count === uids.length
              }
              indeterminate={!loading && count > 0 && count < uids.length}
              disabled={!enabled}
              onChange={(event) =>
                loading
                  ? onToggleKind(upward, node.schemaUid, event.target.checked)
                  : onToggleMany(uids, event.target.checked)
              }
              sx={{ p: 0.5 }}
            />
          </span>
        </Tooltip>
        <Typography variant="body2" noWrap>
          {schemaName(schema, node.schemaUid)}
        </Typography>
        {loading ? (
          <CircularProgress size={12} />
        ) : (
          <Typography variant="caption" color="text.secondary">
            {count} of {uids.length}
          </Typography>
        )}
      </Stack>
      {node.children.map((child) => (
        <SchemaRow
          key={child.schemaUid}
          node={child}
          depth={depth + 1}
          upward={upward}
          index={index}
          chosen={chosen}
          kindChoices={kindChoices}
          aboveLeftOut={leftOut}
          onToggleMany={onToggleMany}
          onToggleKind={onToggleKind}
        />
      ))}
    </>
  )
}

/** A tree in a box with its title on the border, like an outlined field. */
function TreeBox({
  label,
  children,
}: {
  label: string
  children: ReactElement[]
}): ReactElement {
  return (
    <OutlinedFormControl label={label} fullWidth>
      <Box
        sx={{
          // Outranks the row layout the outlined content is given.
          '&&': { flexDirection: 'column', alignItems: 'stretch', gap: 0, py: 1 },
        }}
      >
        {children}
      </Box>
    </OutlinedFormControl>
  )
}

interface SelectionTreeDialogProps {
  itemUids: string[]
  /** Whether the items are being put into the project or taken out. */
  select: boolean
  /** The items as they are to be read in the title: one identifier, or how
   * many of what. */
  subject: string
  /** The kinds of the items, where the caller knows them, so the tree by type
   * can be drawn before the trees of items are worked out. */
  schemaUids?: string[]
  /** The trees, where the caller has already worked them out. */
  initialTrees?: SelectionTree[]
  /** Whether to open showing the choice by type rather than by item. Left
   * out, several items open by type and one by item. */
  byTypeAtStart?: boolean
  comment?: string | null
  tags?: string[] | null
  additiveTags?: boolean
  onClose: () => void
  onApplied: () => void
  onError: (error: unknown) => void
}

/**
 * Removing items from the project or restoring them, with what goes with
 * them chosen from their parents and their children. What the schema says
 * goes with them starts ticked; a curator can leave out any item, and what is
 * below it with it, but cannot choose an item without its parents. What that
 * leaves short of its schema is shown before it is done, and marked not valid
 * after.
 *
 * The choice is shown by item, or by type: every item of a kind, such as all
 * the blocks under the cases being removed, ticked or left out at once. Both
 * are views of the same choice, and switching keeps it.
 *
 * Mount it only while open.
 */
export default function SelectionTreeDialog({
  itemUids,
  select,
  subject,
  schemaUids,
  initialTrees,
  byTypeAtStart,
  comment: initialComment = null,
  tags: initialTags = null,
  additiveTags = false,
  onClose,
  onApplied,
  onError,
}: SelectionTreeDialogProps): ReactElement {
  const schema = useSchemaContext()
  const [comment, setComment] = useState(initialComment)
  const [tags, setTags] = useState<string[]>(initialTags ?? [])
  const [newTagNames, setNewTagNames] = useState<string[]>([])
  const [ticked, setTicked] = useState<Set<string> | null>(null)
  // Choices made by type before the trees arrived, applied over the defaults
  // once they do.
  const [kindChoices, setKindChoices] = useState<KindChoices>(new Map())
  const [expandedChosen, setExpanded] = useState<Set<string> | null>(null)
  // A bulk action is chosen for by kind, one item by what is under it; the
  // other view is a switch away, over the same choice.
  const [byType, setByType] = useState(byTypeAtStart ?? itemUids.length > 1)

  const treesQuery = useQuery({
    queryKey: queryKeys.item.selectionTrees(itemUids, select),
    queryFn: async () => await itemApi.selectionTrees(itemUids, select),
    initialData: initialTrees,
    staleTime: initialTrees === undefined ? 0 : Infinity,
    gcTime: 0,
  })
  const trees = treesQuery.data
  const index = useMemo(
    () => (trees === undefined ? undefined : indexTrees(trees)),
    [trees],
  )
  const defaultTicked = useMemo(
    () => (index === undefined ? new Set<string>() : defaultsOf(index)),
    [index],
  )

  /** The parents of every item asked for, each shown once where several
   * items share it. */
  const parentNodes = useMemo(() => {
    const seen = new Set<string>()
    return (trees ?? [])
      .flatMap((tree) => tree.up)
      .filter((node) => (seen.has(node.uid) ? false : (seen.add(node.uid), true)))
  }, [trees])
  /** With one item asked for, its children are the top of the tree; with
   * several, each item heads its own. */
  const grouped = (trees?.length ?? 0) > 1
  const childGroups = useMemo(
    () => (trees ?? []).filter((tree) => tree.down.length > 0),
    [trees],
  )
  const parentUidsByKind = useMemo(() => uidsByKindOf(parentNodes), [parentNodes])
  const childUidsByKind = useMemo(
    () => uidsByKindOf(childGroups.flatMap((tree) => tree.down)),
    [childGroups],
  )

  /** What is ticked: the defaults with any choice by type made before the
   * trees arrived laid over them, in the order they were made, until the
   * first choice after, which takes it from there. */
  const currentTicked = useMemo(() => {
    if (ticked !== null) {
      return ticked
    }
    const next = new Set(defaultTicked)
    kindChoices.forEach((checked, key) => {
      const [direction, schemaUid] = key.split('/')
      const byKind = direction === 'up' ? parentUidsByKind : childUidsByKind
      ;(byKind.get(schemaUid) ?? []).forEach((uid) =>
        checked ? next.add(uid) : next.delete(uid),
      )
    })
    return next
  }, [ticked, defaultTicked, kindChoices, parentUidsByKind, childUidsByKind])
  const chosen = useMemo(
    () => (index === undefined ? new Set<string>() : chosenOf(index, currentTicked)),
    [index, currentTicked],
  )

  // Where the trees open when the dialog does, worked out from what is chosen
  // by default and not changed by ticking after.
  const defaultExpanded = useMemo(() => {
    if (index === undefined) {
      return new Set<string>()
    }
    const defaultChosen = chosenOf(index, defaultTicked)
    const childRows = childGroups.flatMap((tree) =>
      rowsOf(tree.down, `down/${tree.uid}`, grouped ? 1 : 0),
    )
    // Each item heading its own tree is a level above its children: open
    // only where something below it is left out.
    const openGroups =
      grouped && firstMixedDepth(childRows, defaultChosen) !== undefined
        ? childGroups.map((tree) => `down/${tree.uid}`)
        : []
    return new Set([
      ...openAtStart(rowsOf(parentNodes, 'up', 0), defaultChosen),
      ...openAtStart(childRows, defaultChosen),
      ...openGroups,
    ])
  }, [index, defaultTicked, parentNodes, childGroups, grouped])
  const expanded = expandedChosen ?? defaultExpanded

  /** What is sent: every chosen node, and what goes with the chosen ones. */
  const items = useMemo(() => {
    if (index === undefined) {
      return []
    }
    const all = new Set(chosen)
    chosen.forEach((uid) =>
      index.nodes.get(uid)?.withIt.forEach((other) => all.add(other.uid)),
    )
    return [...all].sort()
  }, [index, chosen])

  const previewQuery = useQuery({
    queryKey: queryKeys.item.selectPreview(itemUids, { select, items }),
    queryFn: async () =>
      await itemApi.selectMany({
        itemUids,
        select,
        items,
        comment: null,
        tags: null,
        additiveTags: false,
        dryRun: true,
      }),
    enabled: index !== undefined,
    staleTime: 0,
    gcTime: 0,
  })

  const applyMutation = useMutation({
    mutationFn: async () =>
      await itemApi.selectMany({
        itemUids,
        select,
        items,
        comment,
        tags,
        additiveTags,
      }),
    onSuccess: () => {
      onApplied()
      onClose()
    },
    onError,
  })

  const toggleMany = (uids: string[], checked: boolean): void => {
    const next = new Set(currentTicked)
    uids.forEach((uid) => (checked ? next.add(uid) : next.delete(uid)))
    setTicked(next)
  }
  const toggle = (uid: string, checked: boolean): void => toggleMany([uid], checked)
  const toggleKind = (upward: boolean, schemaUid: string, checked: boolean): void => {
    const next = new Map(kindChoices)
    // Deleted first, so a kind chosen again moves to the end and is laid
    // over the defaults after anything chosen since.
    next.delete(kindKey(upward, schemaUid))
    next.set(kindKey(upward, schemaUid), checked)
    setKindChoices(next)
  }

  // The kinds come from the schema, so the tree by type is there at once; what
  // the trees hold of each kind is filled in when they arrive.
  const loaded = trees !== undefined && index !== undefined
  const startSchemas = schemaUids ?? trees?.map((tree) => tree.schemaUid)
  const startKey =
    startSchemas === undefined ? undefined : [...new Set(startSchemas)].sort().join(',')
  const kindsUp = useMemo(
    () =>
      startKey === undefined
        ? undefined
        : kindTreeOf(schema, startKey.split(','), true),
    [schema, startKey],
  )
  const kindsDown = useMemo(
    () =>
      startKey === undefined
        ? undefined
        : kindTreeOf(schema, startKey.split(','), false),
    [schema, startKey],
  )
  const parentSchemas = useMemo(
    () =>
      kindsUp === undefined || !loaded
        ? kindsUp
        : countKinds(kindsUp, parentUidsByKind),
    [kindsUp, loaded, parentUidsByKind],
  )
  const childSchemas = useMemo(
    () =>
      kindsDown === undefined || !loaded
        ? kindsDown
        : countKinds(kindsDown, childUidsByKind),
    [kindsDown, loaded, childUidsByKind],
  )
  const anythingByType =
    (parentSchemas?.length ?? 0) > 0 || (childSchemas?.length ?? 0) > 0
  const anythingByItem = parentNodes.length > 0 || childGroups.length > 0
  const anything = loaded ? anythingByItem : anythingByType

  const expand = (path: string): void => {
    const next = new Set(expanded)
    if (next.has(path)) {
      next.delete(path)
    } else {
      next.add(path)
    }
    setExpanded(next)
  }

  const rowProps = {
    index: index as TreeIndex,
    chosen,
    expanded,
    onToggle: toggle,
    onExpand: expand,
  }
  return (
    <Dialog open onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        {select
          ? `Restore ${subject} to the project?`
          : `Remove ${subject} from the project?`}
      </DialogTitle>
      <DialogContent dividers>
        {treesQuery.isError && (
          <Alert severity="error">Could not work out what goes with it.</Alert>
        )}
        <Stack spacing={2.5} sx={{ pt: 1 }}>
          {loaded && !anythingByItem && (
            <Typography variant="body2" color="text.secondary">
              Nothing else changes with it.
            </Typography>
          )}
          {anything && (
            <ToggleButtonGroup
              size="small"
              exclusive
              value={byType ? 'type' : 'item'}
              onChange={(_, value: string | null) => {
                if (value !== null) {
                  setByType(value === 'type')
                }
              }}
              sx={{ alignSelf: 'flex-start' }}
            >
              <ToggleButton value="type">By type</ToggleButton>
              <ToggleButton value="item">By item</ToggleButton>
            </ToggleButtonGroup>
          )}
          {!loaded &&
            (!byType || startSchemas === undefined) &&
            !treesQuery.isError && <LinearProgress />}
          {byType && parentSchemas !== undefined && parentSchemas.length > 0 && (
            <TreeBox label="Parents">
              {parentSchemas.map((node) => (
                <SchemaRow
                  key={node.schemaUid}
                  node={node}
                  depth={0}
                  upward={true}
                  index={index}
                  chosen={chosen}
                  kindChoices={kindChoices}
                  onToggleMany={toggleMany}
                  onToggleKind={toggleKind}
                />
              ))}
            </TreeBox>
          )}
          {byType && childSchemas !== undefined && childSchemas.length > 0 && (
            <TreeBox label="Children">
              {childSchemas.map((node) => (
                <SchemaRow
                  key={node.schemaUid}
                  node={node}
                  depth={0}
                  upward={false}
                  index={index}
                  chosen={chosen}
                  kindChoices={kindChoices}
                  onToggleMany={toggleMany}
                  onToggleKind={toggleKind}
                />
              ))}
            </TreeBox>
          )}
          {!byType && loaded && parentNodes.length > 0 && (
            <TreeBox label="Parents">
              {parentNodes.map((node) => (
                <TreeRow
                  key={node.uid}
                  node={node}
                  path={`up/${node.uid}`}
                  depth={0}
                  {...rowProps}
                />
              ))}
            </TreeBox>
          )}
          {!byType && loaded && childGroups.length > 0 && (
            <TreeBox label="Children">
              {grouped
                ? childGroups.map((tree) => (
                    <Box key={tree.uid}>
                      <Stack
                        direction="row"
                        spacing={0.5}
                        sx={{ alignItems: 'center', minHeight: 32 }}
                      >
                        <IconButton
                          size="small"
                          onClick={() => expand(`down/${tree.uid}`)}
                        >
                          {expanded.has(`down/${tree.uid}`) ? (
                            <ExpandMore fontSize="small" />
                          ) : (
                            <ChevronRight fontSize="small" />
                          )}
                        </IconButton>
                        <Typography variant="body2" sx={{ fontWeight: 500 }} noWrap>
                          {schemaName(schema, tree.schemaUid)} {tree.identifier}
                        </Typography>
                      </Stack>
                      {expanded.has(`down/${tree.uid}`) &&
                        tree.down.map((node) => (
                          <TreeRow
                            key={node.uid}
                            node={node}
                            path={`down/${tree.uid}/${node.uid}`}
                            depth={1}
                            {...rowProps}
                          />
                        ))}
                    </Box>
                  ))
                : childGroups.flatMap((tree) =>
                    tree.down.map((node) => (
                      <TreeRow
                        key={node.uid}
                        node={node}
                        path={`down/${tree.uid}/${node.uid}`}
                        depth={0}
                        {...rowProps}
                      />
                    )),
                  )}
            </TreeBox>
          )}
          {previewQuery.data !== undefined &&
            previewQuery.data.leftInvalid.length > 0 && (
              <Alert severity="warning" variant="outlined">
                <ChangeGroup
                  title="Left not valid, to settle before the batch completes"
                  changes={previewQuery.data.leftInvalid}
                  color="error"
                />
              </Alert>
            )}
          <TextField
            label="Comment"
            size="small"
            value={comment ?? ''}
            onChange={(event) => setComment(event.target.value)}
            fullWidth
          />
          <DisplayItemTags
            tagUids={tags}
            newTagNames={newTagNames}
            editable={true}
            handleTagsUpdate={setTags}
            setNewTags={setNewTagNames}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Typography variant="caption" color="text.secondary" sx={{ mr: 'auto', ml: 2 }}>
          {items.length === 0
            ? 'Nothing else changes.'
            : `${items.length} other item${items.length === 1 ? '' : 's'} change with it.`}
        </Typography>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          variant="contained"
          disabled={index === undefined || applyMutation.isPending}
          onClick={() => applyMutation.mutate()}
        >
          {select ? 'Restore' : 'Remove'}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
