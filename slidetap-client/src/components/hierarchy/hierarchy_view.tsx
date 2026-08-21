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
  Check,
  Close,
  ChevronRight,
  DeleteOutlined,
  DragHandle,
  ExpandMore,
  ErrorOutlined,
  Inventory2,
  Search,
  Undo,
} from '@mui/icons-material'
import {
  Box,
  Chip,
  IconButton,
  InputAdornment,
  LinearProgress,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
  alpha,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useMemo, useState, type ReactElement } from 'react'
import { useDetailDock } from 'src/components/item/detail_dock'
import SplitPanel from 'src/components/split_panel'
import { ValueActions } from 'src/components/table/value_actions'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { AttributeValueType } from 'src/models/attribute_value_type'
import { AttributeValueField } from 'src/models/table_item'
import type { HierarchyNode } from 'src/models/hierarchy'
import type { ItemSchema } from 'src/models/schema/item_schema'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import type { AttributeValueLayout } from 'src/models/schema/attribute_value_layout'
import type {
  HierarchyLayout,
  HierarchyLevelLayout,
} from 'src/models/schema/hierarchy_layout'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'

interface HierarchyViewProps {
  projectUid: string
  itemUid: string
  layout: HierarchyLayout
}

/** What is being dragged, so every cell can say whether it would take it. */
interface Dragged {
  itemUid: string
  schemaUid: string
}

/**
 * One path through the tree: a cell per level, and the images hanging off the
 * end of it.
 *
 * A row is an item and the images of it, rather than the item and then its
 * image on a line of its own: an image usually belongs to exactly one item, so
 * a level of its own would repeat that item on every second row and say
 * nothing. Something parked further up comes out as a row whose left-hand
 * cells are empty, which is the ragged edge that says it is not where it
 * should be.
 */
interface Row {
  /** The rows this one stands in for while its group is folded, if any. */
  folded?: Row[]
  key: string
  cells: (HierarchyNode | null)[]
  inline: HierarchyNode[]
}

/** What the row calls the item: the name where there is one, since a name is
 * what tells it from its siblings, where the identifier usually repeats what
 * the column already says. Never in pseudonym mode, where only the pseudonym
 * is to be shown. */
function labelOf(node: HierarchyNode, pseudonymMode: boolean): string {
  return pseudonymMode || node.name === null
    ? getDisplayIdentifier(node, pseudonymMode)
    : node.name
}

/** What a search is being run against: what names the item, or one value the
 * layout offered. Chosen rather than searched all at once — a term that hits
 * identifiers and values of every kind at once answers a question nobody
 * asked. */
const BY_IDENTIFIER = 'identifier'
type SearchTarget = typeof BY_IDENTIFIER | AttributeValueLayout

/** Whether the row itself answers to the search. */
function matches(node: HierarchyNode, search: string, target: SearchTarget): boolean {
  const term = search.toLowerCase()
  if (target === BY_IDENTIFIER) {
    return (
      node.identifier.toLowerCase().includes(term) ||
      (node.name?.toLowerCase().includes(term) ?? false) ||
      (node.pseudonym?.toLowerCase().includes(term) ?? false)
    )
  }
  const attribute = node.attributes[target.tag]
  if (attribute === undefined) {
    return false
  }
  const value =
    target.field === AttributeValueField.MAPPABLE
      ? attribute.mappableValue
      : attribute.displayValue
  return value?.toLowerCase().includes(term) ?? false
}

/**
 * The tree with everything that has no match in it cut away, or null when
 * nothing under here matches.
 *
 * Kept nested rather than filtered flat: where a thing sits is half of what
 * the reader came to check. A row that matches keeps everything under it,
 * since what is under an item is why the item was looked for.
 */
function prune(
  node: HierarchyNode,
  search: string,
  target: SearchTarget,
): HierarchyNode | null {
  if (matches(node, search, target)) {
    return node
  }
  const children = node.children
    .map((child) => prune(child, search, target))
    .filter((child) => child !== null)
  return children.length > 0 ? { ...node, children } : null
}

/**
 * What a folded group stands for: how many of each kind it holds, and how much
 * of it is not valid.
 *
 * Counted rather than listed: the point of folding is that the group has been
 * dealt with, and what is worth keeping on screen is enough to notice if that
 * turns out not to be true.
 */
function summarise(rows: Row[]): string {
  const counted = new Map<string, { total: number; invalid: number }>()
  const count = (node: HierarchyNode): void => {
    const entry = counted.get(node.schemaDisplayName) ?? { total: 0, invalid: 0 }
    counted.set(node.schemaDisplayName, {
      total: entry.total + 1,
      invalid: entry.invalid + (node.valid ? 0 : 1),
    })
  }
  const seen = new Set<string>()
  rows.forEach((row) => {
    ;[...row.cells.slice(1), ...row.inline].forEach((node) => {
      if (node === null || seen.has(node.uid)) return
      seen.add(node.uid)
      count(node)
    })
  })
  return [...counted]
    .map(([name, { total, invalid }]) =>
      invalid === 0 ? `${total} ${name}` : `${total} ${name} (${invalid} not valid)`,
    )
    .join(' · ')
}

export default function HierarchyView({
  projectUid,
  itemUid,
  layout,
}: HierarchyViewProps): ReactElement {
  const dock = useDetailDock(projectUid)
  const rootSchema = useSchemaContext()
  const queryClient = useQueryClient()
  const { pseudonymMode } = usePseudonym()
  const [search, setSearch] = useState('')
  const [targetTag, setTargetTag] = useState<string>(BY_IDENTIFIER)
  // Folded groups, by the uid of the item at the top of them. For working
  // through a tree too tall for the window: what has been checked folds away
  // and what is left is what is left to do.
  const [folded, setFolded] = useState<ReadonlySet<string>>(new Set())
  const [dragged, setDragged] = useState<Dragged | null>(null)
  // The rows the cell under the pointer covers. Everything overlapping them
  // lights up, which reads both ways: hovering a group takes in all its
  // children, hovering one child takes in what it came from.
  const [hovered, setHovered] = useState<{ start: number; end: number } | null>(null)
  const hierarchyQuery = useQuery({
    queryKey: queryKeys.item.hierarchy(itemUid, layout.uid),
    queryFn: async () => await itemApi.getHierarchy(itemUid, layout.uid),
  })

  /** The schema of any kind of item, since a layout may name any of them. */
  const schemaOf = useCallback(
    (schemaUid: string): ItemSchema | undefined =>
      rootSchema.samples[schemaUid] ??
      rootSchema.images[schemaUid] ??
      rootSchema.observations[schemaUid] ??
      rootSchema.annotations[schemaUid],
    [rootSchema],
  )

  const levelOf = useCallback(
    (schemaUid: string): HierarchyLevelLayout | undefined =>
      layout.levels.find((level) => level.schemaUid === schemaUid),
    [layout],
  )

  // A column per level that stands on its own, and one column at the end for
  // the levels that sit beside their parent. Which is which is the layout's
  // choice, not the view's.
  const columns = useMemo(
    () => layout.levels.filter((level) => !level.inline),
    [layout],
  )
  const inlineLevels = useMemo(
    () => layout.levels.filter((level) => level.inline),
    [layout],
  )
  const isInline = useCallback(
    (node: HierarchyNode) =>
      inlineLevels.some((level) => level.schemaUid === node.schemaUid),
    [inlineLevels],
  )

  const movable = useMemo(
    () =>
      new Set(
        layout.levels.filter((level) => level.movable).map((level) => level.schemaUid),
      ),
    [layout],
  )

  const deletable = useMemo(
    () =>
      new Set(
        layout.levels
          .filter((level) => level.deletable)
          .map((level) => level.schemaUid),
      ),
    [layout],
  )

  // Everything the layout shows can also be searched by, named as the schema
  // names it. Taken from the levels in order, so the choices read down the
  // tree the way the columns do.
  const searchable = useMemo(
    () =>
      layout.levels.flatMap((level) =>
        level.attributes.map((attribute) => {
          const schema =
            rootSchema.samples[level.schemaUid] ?? rootSchema.images[level.schemaUid]
          return {
            attribute,
            label:
              (
                schema?.attributes[attribute.tag] ??
                schema?.privateAttributes[attribute.tag]
              )?.displayName ?? attribute.tag,
          }
        }),
      ),
    [layout, rootSchema],
  )
  const target =
    searchable.find(({ attribute }) => attribute.tag === targetTag)?.attribute ??
    BY_IDENTIFIER

  /**
   * Whether the dragged item may hang under this one.
   *
   * Read off the relations rather than declared again in the layout: a
   * relation between two schemas is what says the pairing exists, and it is
   * the same statement the validator holds the data to. An orphan relation is
   * not somewhere to move something — it is where things end up for want of
   * anywhere better.
   */
  const accepts = useCallback(
    (dragging: Dragged, node: HierarchyNode): boolean => {
      if (dragging.itemUid === node.uid) {
        return false
      }
      const image = rootSchema.images[dragging.schemaUid]
      if (image !== undefined) {
        return image.samples.some(
          (relation) => !relation.orphan && relation.sampleUid === node.schemaUid,
        )
      }
      const sample = rootSchema.samples[dragging.schemaUid]
      return (
        sample?.parents.some((relation) => relation.parentUid === node.schemaUid) ??
        false
      )
    },
    [rootSchema],
  )

  const moveMutation = useMutation({
    mutationFn: async ({
      movedUid,
      targetUid,
    }: {
      movedUid: string
      targetUid: string
    }) => await itemApi.move(movedUid, targetUid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })

  /** Taking an item out of the project, and putting it back.
   *
   * The same call either way, since taking something out is only a flag: what
   * the laboratory registered stays where it is, and the row it was taken out
   * from is where it is put back. */
  const selectMutation = useMutation({
    mutationFn: async ({ itemUid, select }: { itemUid: string; select: boolean }) =>
      await itemApi.select(itemUid, {
        select,
        comment: null,
        tags: null,
        additiveTags: false,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })

  const allRows = useMemo(() => {
    if (hierarchyQuery.data === undefined) {
      return []
    }
    const roots =
      search === ''
        ? hierarchyQuery.data.children
        : hierarchyQuery.data.children
            .map((child) => prune(child, search, target))
            .filter((child) => child !== null)

    const built: Row[] = []
    const walk = (node: HierarchyNode, path: (HierarchyNode | null)[]): void => {
      const inline = node.children.filter(isInline)
      const nested = node.children.filter((child) => !isInline(child))
      const cells = [...path, ...Array<null>(columns.length - path.length).fill(null)]
      if (nested.length === 0 || inline.length > 0) {
        built.push({ key: node.uid, cells, inline })
      }
      nested.forEach((child) => walk(child, [...path, child]))
    }
    // Inline items hanging off the root itself have no path at all, which is
    // the point: nothing above them is filled in. Taken from what the search
    // left, so looking for one that is parked still finds it.
    const rootInline = roots.filter(isInline)
    if (rootInline.length > 0) {
      built.push({
        key: hierarchyQuery.data.uid,
        cells: Array<null>(columns.length).fill(null),
        inline: rootInline,
      })
    }
    roots.filter((node) => !isInline(node)).forEach((node) => walk(node, [node]))
    return built
  }, [hierarchyQuery.data, search, columns, isInline, target])

  // A folded group keeps its first row and says what it stands for; the rest
  // of its rows are dropped. Counted from the rows themselves rather than from
  // the tree, so the count is of what is on screen — a search leaves a folded
  // group saying how many of its rows matched.
  const rows = useMemo(
    () =>
      allRows.reduce<Row[]>((kept, row) => {
        const group = row.cells[0]
        if (group === null || !folded.has(group.uid)) {
          return [...kept, row]
        }
        const last = kept[kept.length - 1]
        if (last?.cells[0]?.uid === group.uid) {
          last.folded = [...(last.folded ?? []), row]
          return kept
        }
        return [...kept, { ...row, folded: [] }]
      }, []),
    [allRows, folded],
  )

  // The widest identifier a column holds, in characters, turned into a width
  // every cell of that column reserves. Measured rather than fixed, since a
  // column of names and a column of pseudonyms are nothing alike.
  const labelWidths = [...columns, ...inlineLevels.slice(0, 1)].map((_, column) => {
    const longest = rows.reduce((width, row) => {
      const node =
        column === columns.length ? (row.inline[0] ?? null) : row.cells[column]
      return node === null
        ? width
        : Math.max(width, labelOf(node, pseudonymMode).length)
    }, 1)
    // The chip's own padding and its chevron, on top of the text it holds.
    return `calc(${longest}ch + 62px)`
  })

  // A hue per outermost group, a stronger tint of it per group inside it.
  // Background rather than chips: the chips carry red for invalid and orange
  // for parked, and those have to stay the loudest thing on the row.
  const tints = (() => {
    const outer: string[] = []
    const inner: string[] = []
    return rows.map((row) => {
      const group = row.cells[0]?.uid
      const nested = row.cells[1]?.uid
      if (group === undefined) {
        return undefined
      }
      if (!outer.includes(group)) {
        outer.push(group)
      }
      if (nested !== undefined && !inner.includes(nested)) {
        inner.push(nested)
      }
      const hue = GROUP_HUES[outer.indexOf(group) % GROUP_HUES.length]
      const shade = nested === undefined ? 0 : inner.indexOf(nested) % 2
      return alpha(hue, 0.05 + shade * 0.05)
    })
  })()

  /** Whether a cell starting at this row and covering this many shares any row
   * with what the pointer is on. */
  const overlaps = (start: number, span: number): boolean =>
    hovered !== null && start < hovered.end && start + span > hovered.start

  if (hierarchyQuery.isLoading) {
    return <LinearProgress />
  }
  if (hierarchyQuery.data === undefined) {
    return <Typography sx={{ p: 2 }}>Nothing to show.</Typography>
  }

  const siblings = rows.flatMap((row) => [
    ...row.cells.filter((cell) => cell !== null).map((cell) => cell.uid),
    ...row.inline.map((item) => item.uid),
  ])

  // One cell over the rows it covers, rather than one cell said once and then
  // blank underneath: a specimen with four slides is one specimen, and the
  // blanks under it were the reader's job to interpret. Spanning also gives
  // the cell height to stack what it says, so the column can be narrow.
  const spans = rows.map((row, index) =>
    row.cells.map((cell, column) => {
      if (cell === null) {
        return { node: null, span: 1 }
      }
      if (rows[index - 1]?.cells[column]?.uid === cell.uid) {
        return null
      }
      let span = 1
      while (rows[index + span]?.cells[column]?.uid === cell.uid) {
        span += 1
      }
      return { node: cell, span }
    }),
  )

  return (
    <SplitPanel fillHeight panel={dock.panel}>
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
          <TextField
            size="small"
            placeholder="Search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            sx={{ width: 260 }}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <Search fontSize="small" />
                  </InputAdornment>
                ),
              },
            }}
          />
          {/* Only where the layout offered something else to search by: a
              chooser with one choice in it is a label. */}
          {searchable.length > 0 && (
            <TextField
              select
              size="small"
              value={targetTag}
              onChange={(event) => setTargetTag(event.target.value)}
              sx={{ minWidth: 160 }}
            >
              <MenuItem value={BY_IDENTIFIER}>Identifier</MenuItem>
              {searchable.map(({ attribute, label }) => (
                <MenuItem key={attribute.tag} value={attribute.tag}>
                  {label}
                </MenuItem>
              ))}
            </TextField>
          )}
        </Stack>
        <Box sx={{ flexGrow: 1, minHeight: 0, overflow: 'auto' }}>
          {rows.length === 0 ? (
            <Typography sx={{ p: 2 }}>
              {search === '' ? 'Nothing to show.' : `Nothing matches ${search}.`}
            </Typography>
          ) : (
            <Table size="small" stickyHeader>
              <TableHead>
                <TableRow>
                  {columns.map((level) => (
                    <TableCell key={level.schemaUid}>
                      {schemaOf(level.schemaUid)?.displayName}
                    </TableCell>
                  ))}
                  {inlineLevels.length > 0 && (
                    <TableCell sx={{ width: '1%', whiteSpace: 'nowrap' }}>
                      {inlineLevels
                        .map((level) => schemaOf(level.schemaUid)?.displayName)
                        .join(' / ')}
                    </TableCell>
                  )}
                  {/* Takes whatever width is left, so the columns before it
                      keep to their content and stay next to each other. */}
                  <TableCell sx={{ width: '100%' }} />
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row, index) => (
                  <TableRow
                    key={row.key}
                    sx={{
                      bgcolor: tints[index],
                      // A rule where a group starts and a faint one inside it:
                      // the eye needs to know which specimen a row belongs to
                      // once the specimen cell has scrolled out of reach, and
                      // a line does that without spending colour, which is
                      // already saying "not valid" and "parked here".
                      ...(index > 0 &&
                        rows[index - 1].cells[0]?.uid !== row.cells[0]?.uid && {
                          '& td': { borderTop: 1, borderTopColor: 'text.disabled' },
                        }),
                    }}
                  >
                    {spans[index].map((span, column) =>
                      // Everything past the folded group's own column is one
                      // line saying what was folded away.
                      row.folded !== undefined && column > 0 ? null : span ===
                        null ? null : (
                        <TableCell
                          key={column}
                          rowSpan={span.span}
                          onMouseEnter={() =>
                            setHovered({ start: index, end: index + span.span })
                          }
                          onMouseLeave={() => setHovered(null)}
                          // Sized to what is in it, with the slack left to the
                          // spacer at the end: shared out evenly, a column of
                          // short identifiers ends up as wide as one of long
                          // values, and the gap between them is what the eye
                          // has to cross.
                          sx={{
                            verticalAlign: 'top',
                            whiteSpace: 'nowrap',
                            width: '1%',
                            // Lit per cell rather than per row: a cell that
                            // spans is drawn in the row it starts in, so a row
                            // of colour would light the specimen when the first
                            // of its slides is hovered and not when the second
                            // is.
                            ...(overlaps(index, span.span) && {
                              bgcolor: 'action.hover',
                            }),
                          }}
                        >
                          {/* A row, so the fold control sits beside what it
                              folds rather than above it — the cell inside may
                              be a stack, and the control belongs to all of
                              it. */}
                          <Box sx={{ display: 'flex', alignItems: 'flex-start' }}>
                            {/* Only the outermost column folds: it is the group
                              a reviewer finishes and puts aside. */}
                            {column === 0 && span.node !== null && (
                              <Tooltip
                                title={
                                  folded.has(span.node.uid)
                                    ? 'Unfold'
                                    : 'Fold this away'
                                }
                              >
                                <IconButton
                                  size="small"
                                  sx={{ p: 0, mr: 0.5 }}
                                  onClick={() =>
                                    setFolded((current) => {
                                      const next = new Set(current)
                                      const uid = span.node?.uid
                                      if (uid === undefined) return next
                                      if (!next.delete(uid)) next.add(uid)
                                      return next
                                    })
                                  }
                                >
                                  {folded.has(span.node.uid) ? (
                                    <ChevronRight fontSize="small" />
                                  ) : (
                                    <ExpandMore fontSize="small" />
                                  )}
                                </IconButton>
                              </Tooltip>
                            )}
                            {span.node !== null && (
                              <ItemCell
                                node={span.node}
                                level={columns[column]}
                                // Stacked only where the cell has the height for
                                // it: a cell one row tall would push everything
                                // below it down to say the same thing sideways.
                                stacked={span.span > 1}
                                labelWidth={labelWidths[column]}
                                movable={movable.has(span.node.schemaUid)}
                                deletable={deletable.has(span.node.schemaUid)}
                                dragged={dragged}
                                accepts={accepts}
                                pseudonymMode={pseudonymMode}
                                onDrag={setDragged}
                                onDrop={(movedUid, targetUid) =>
                                  moveMutation.mutate({ movedUid, targetUid })
                                }
                                onSelect={(itemUid, select) =>
                                  selectMutation.mutate({ itemUid, select })
                                }
                                onOpen={() => dock.open(span.node.uid, siblings)}
                              />
                            )}
                          </Box>
                        </TableCell>
                      ),
                    )}
                    {row.folded !== undefined ? (
                      <TableCell
                        colSpan={columns.length}
                        sx={{ color: 'text.secondary', whiteSpace: 'nowrap' }}
                      >
                        {summarise([row, ...row.folded])}
                      </TableCell>
                    ) : (
                      <TableCell
                        onMouseEnter={() =>
                          setHovered({ start: index, end: index + 1 })
                        }
                        onMouseLeave={() => setHovered(null)}
                        sx={{
                          verticalAlign: 'top',
                          whiteSpace: 'nowrap',
                          width: '1%',
                          ...(overlaps(index, 1) && { bgcolor: 'action.hover' }),
                        }}
                      >
                        {row.inline.map((image) => (
                          <ItemCell
                            key={image.uid}
                            node={image}
                            // The level of this image's own schema: a model may
                            // have more than one kind of image, and each says
                            // what it shows for itself.
                            level={levelOf(image.schemaUid)}
                            labelWidth={labelWidths[columns.length]}
                            movable={movable.has(image.schemaUid)}
                            deletable={deletable.has(image.schemaUid)}
                            dragged={dragged}
                            accepts={accepts}
                            pseudonymMode={pseudonymMode}
                            onDrag={setDragged}
                            onDrop={(movedUid, targetUid) =>
                              moveMutation.mutate({ movedUid, targetUid })
                            }
                            onSelect={(itemUid, select) =>
                              selectMutation.mutate({ itemUid, select })
                            }
                            onOpen={() => dock.open(image.uid, siblings)}
                          />
                        ))}
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </Box>
      </Box>
    </SplitPanel>
  )
}

interface ItemCellProps {
  node: HierarchyNode
  level: HierarchyLevelLayout | undefined
  /** Lay what the cell says out down the cell rather than across it, for a
   * cell tall enough to have the room. */
  stacked?: boolean
  /** Width to hold for the identifier, so a column lines up under itself. */
  labelWidth: string
  movable: boolean
  /** Whether this item may be taken out of the project from its row. Offered
   * only where nothing hangs under it. */
  deletable: boolean
  dragged: Dragged | null
  accepts: (dragged: Dragged, node: HierarchyNode) => boolean
  pseudonymMode: boolean
  onDrag: (dragged: Dragged | null) => void
  onDrop: (itemUid: string, targetUid: string) => void
  onSelect: (itemUid: string, select: boolean) => void
  onOpen: () => void
}

/** One item: its identifier as the chip it is everywhere else, whatever the
 * layout asks to show about it, and the marks for what is wrong with it. */
function ItemCell({
  node,
  level,
  stacked = false,
  labelWidth,
  movable,
  deletable,
  dragged,
  accepts,
  pseudonymMode,
  onDrag,
  onDrop,
  onSelect,
  onOpen,
}: ItemCellProps): ReactElement {
  const rootSchema = useSchemaContext()
  const itemSchema =
    rootSchema.samples[node.schemaUid] ??
    rootSchema.images[node.schemaUid] ??
    rootSchema.observations[node.schemaUid] ??
    rootSchema.annotations[node.schemaUid]
  const takesDrop = dragged !== null && accepts(dragged, node)
  const label = labelOf(node, pseudonymMode)
  // Only where nothing hangs under it: a slide with an image is a slide that
  // was scanned, and taking it out would take the image with it. What this is
  // for is the other case -- a slide the laboratory registered that nothing in
  // PACS answers to, which only a curator can say is not part of the dataset.
  const removable = deletable && node.children.length === 0

  return (
    <Box
      onDragOver={(event) => {
        // Only where it could land: a cell that takes nothing leaves the cursor
        // saying so rather than accepting and then refusing.
        if (takesDrop) {
          event.preventDefault()
          event.dataTransfer.dropEffect = 'move'
        }
      }}
      onDrop={(event) => {
        if (!takesDrop || dragged === null) return
        event.preventDefault()
        onDrop(dragged.itemUid, node.uid)
        onDrag(null)
      }}
      sx={{
        display: 'flex',
        flexDirection: stacked ? 'column' : 'row',
        alignItems: stacked ? 'flex-start' : 'center',
        gap: 0.5,
        // Takes the width of the cell rather than of what it holds, so what
        // trails it can be put at the cell's edge instead of the content's.
        // Grows where the cell has a fold control beside it, and fills the
        // cell on its own where it has not.
        flexGrow: 1,
        minWidth: 0,
        // Taken out of the project, and kept on screen so it can be put back:
        // faded rather than struck through, since what the row says is still
        // what the laboratory registered.
        ...(!node.selected && { opacity: 0.5 }),
        // Every cell that would take what is being dragged says so, so where a
        // thing may go can be seen before letting go of it.
        ...(takesDrop && {
          outline: '1px dashed',
          outlineColor: 'primary.main',
          borderRadius: 1,
        }),
      }}
    >
      {/* The same handle the overview uses to move a whole entry, so the
          gesture is learned once. The handle is what is dragged rather than
          the cell, which leaves the chip free to be hovered and clicked. */}
      {movable && (
        <Tooltip title="Drag to move this to another item">
          <Box
            draggable
            onDragStart={(event) => {
              const payload: Dragged = { itemUid: node.uid, schemaUid: node.schemaUid }
              event.dataTransfer.setData(HIERARCHY_DRAG_MIME, JSON.stringify(payload))
              event.dataTransfer.effectAllowed = 'move'
              onDrag(payload)
            }}
            onDragEnd={() => onDrag(null)}
            sx={{
              display: 'flex',
              alignItems: 'center',
              cursor: 'grab',
              userSelect: 'none',
              color: 'text.secondary',
              '&:active': { cursor: 'grabbing' },
            }}
          >
            <DragHandle fontSize="small" />
          </Box>
        </Tooltip>
      )}
      {/* The identifier keeps the same width down the whole column, so what
          follows it starts in the same place on every row. Slides numbered 1
          and 10 are a character apart, and without this their stains are too,
          which is enough to stop a column being read down. */}
      <Box sx={{ minWidth: labelWidth, flexShrink: 0 }}>
        <Tooltip title={`${node.schemaDisplayName} ${node.identifier}`}>
          <span>
            <ValueActions value={label} monospace copyable dense onOpen={onOpen} />
          </span>
        </Tooltip>
      </Box>
      {(level?.attributes ?? []).map(({ tag, field }) => {
        const attribute = node.attributes[tag]
        // What the layout asked for: the mapped value says what the item
        // means, the mappable one is what it arrived as, which is what the
        // systems it came from show and what it is checked against.
        const value =
          field === AttributeValueField.MAPPABLE
            ? (attribute?.mappableValue ?? '')
            : (attribute?.displayValue ?? '')
        if (attribute === undefined || value === '') {
          return null
        }
        // Named from wherever the schema keeps it: a level may ask for a
        // private attribute, and it is shown the same way as any other.
        const name =
          (itemSchema?.attributes[tag] ?? itemSchema?.privateAttributes[tag])
            ?.displayName ?? tag
        // A yes or a no is not worth reading on its own — what was asked is the
        // information, so a boolean shows its name and answers with the mark
        // beside it.
        const boolean = attribute.attributeValueType === AttributeValueType.BOOLEAN
        return (
          <Tooltip key={tag} title={name}>
            <Chip
              size="small"
              variant="outlined"
              icon={
                boolean ? (
                  attribute.displayValue === 'True' ? (
                    <Check />
                  ) : (
                    <Close />
                  )
                ) : undefined
              }
              label={boolean ? name : value}
              sx={{ maxWidth: 220 }}
            />
          </Tooltip>
        )
      })}
      {/* Everything that answers "is anything wrong with this one", kept at
          the edge of the cell rather than after the last chip. The question is
          asked of the whole column at once, and a mark that starts wherever
          the row before it happened to end cannot be read down one. */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 0.5,
          flexShrink: 0,
          // Pushed to the far end of the cell, which is the right edge either
          // way round: the end of the row when the cell reads across, the
          // right of the stack when it reads down.
          ...(stacked ? { alignSelf: 'flex-end' } : { ml: 'auto' }),
        }}
      >
        {node.orphan && (
          <Tooltip title="Parked here for want of anywhere better">
            <Inventory2 fontSize="small" sx={{ color: 'warning.main' }} />
          </Tooltip>
        )}
        {!node.valid && (
          <Tooltip title="Not valid">
            <ErrorOutlined fontSize="small" sx={{ color: 'error.main' }} />
          </Tooltip>
        )}
        {/* No confirming step: taking one row out of the project changes a
            flag and nothing else, and the row stays where it is with the way
            back on it. Shown disabled rather than hidden once the batch is
            locked: the choice was there and has been made, and a button that
            vanishes says the row was never one to make it about. */}
        {removable && node.selected && (
          <Tooltip
            title={
              node.locked
                ? 'Its batch is locked, so what it holds is settled'
                : `Take ${node.schemaDisplayName} ${node.identifier} out of the project`
            }
          >
            <span>
              <IconButton
                size="small"
                color="error"
                sx={{ p: 0 }}
                disabled={node.locked}
                onClick={() => onSelect(node.uid, false)}
              >
                <DeleteOutlined fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        )}
        {/* Only the levels the layout hands the choice to: a row faded
            because what it hangs under was taken out is put back by putting
            that back, not by arguing with it here. */}
        {deletable && !node.selected && (
          <Tooltip
            title={
              node.locked
                ? 'Taken out of the project, and its batch is locked'
                : 'Taken out of the project. Put it back'
            }
          >
            <span>
              <IconButton
                size="small"
                sx={{ p: 0 }}
                disabled={node.locked}
                onClick={() => onSelect(node.uid, true)}
              >
                <Undo fontSize="small" />
              </IconButton>
            </span>
          </Tooltip>
        )}
      </Box>
    </Box>
  )
}

const HIERARCHY_DRAG_MIME = 'application/x-hierarchy-item'

/** Hues to hand out to groups, in order. Distinct enough to tell apart at
 * the low opacity they are used at, and none of them the red or orange that
 * mean something on a row. */
const GROUP_HUES = ['#1976d2', '#7b1fa2', '#00796b', '#5d4037', '#455a64']
