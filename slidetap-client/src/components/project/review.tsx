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
  ChevronLeft,
  ChevronRight,
  Flag,
  History,
  NavigateBefore,
  NavigateNext,
  Rule,
  SortByAlpha,
  Save,
  Undo,
} from '@mui/icons-material'
import {
  Box,
  Divider,
  IconButton,
  LinearProgress,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useMutation, useQueries, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactElement } from 'react'
import { useSearchParams } from 'react-router-dom'
import HierarchyView from 'src/components/hierarchy/hierarchy_view'
import ImagesForItem from 'src/components/image/images_for_item_page'
import { useDetailDock } from 'src/components/item/detail_dock'
import OverviewView from 'src/components/overview/overview_view'
import type { OverviewEditState } from 'src/components/overview/overview_view'
import SplitPanel from 'src/components/split_panel'
import type {
  AnyReviewPanelLayout,
  ReviewTabLayout,
} from 'src/models/schema/review_layout'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import type { Batch } from 'src/models/batch'
import type { Project } from 'src/models/project'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import { ReviewStatus, ReviewStatusStrings } from 'src/models/review_status'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'

/** Stands for no status filter in the select, which cannot hold undefined. */
const ALL_STATUSES = 'all'
/** The same, for the kind of item reviewed. */
const ALL_TYPES = 'all'

enum Sort {
  Identifier = 'identifier',
  LastSaved = 'lastSaved',
}

function formatSaved(lastSaved: string | null): string {
  if (lastSaved === null) {
    return 'Never saved'
  }
  return new Date(lastSaved).toLocaleString(undefined, {
    dateStyle: 'short',
    timeStyle: 'short',
  })
}

const EMPTY_QUEUE: Record<ReviewStatus, string> = {
  [ReviewStatus.NotReviewed]: 'Everything here has been flagged or reviewed.',
  [ReviewStatus.Flagged]: 'Nothing needs review.',
  [ReviewStatus.Reviewed]: 'Nothing has been reviewed.',
}

interface ReviewProps {
  project: Project
  batch: Batch
}

/** What to call a queue of this many of these: "8 cases", but a name written
 * as an acronym is left as it is — "8 WSI", not "8 wsis". */
function queueLabel(displayName: string, count: number): string {
  if (displayName === displayName.toLocaleUpperCase()) {
    return displayName
  }
  const name = displayName.toLocaleLowerCase()
  return count === 1 ? name : `${name}s`
}

/** How much of the tab a panel asked for, out of twelve. */
function panelWidth(panel: AnyReviewPanelLayout): number | undefined {
  if (panel.width === null) {
    return undefined
  }
  return panel.width.lg ?? panel.width.md ?? panel.width.xs
}

/**
 * Works through the items of a batch flagged for review, one at a time.
 *
 * Separate from curate rather than a mode of it: curating is picking items out
 * of a list and operating on them, reviewing is being handed the next thing
 * that needs a decision. The queue on the left is there to jump about in, but
 * the normal way through it is next and previous.
 *
 * Per batch rather than per project: a batch is what is imported, and the
 * import is what raises most of the flags, so it is also what gets worked
 * through.
 *
 * Each tab is a set of panels the schema lays out — an overview, a hierarchy,
 * the images — so what a reviewer is shown is a schema decision, not a
 * component.
 */
export default function Review({ project, batch }: ReviewProps): ReactElement {
  const rootSchema = useSchemaContext()
  const queryClient = useQueryClient()
  const { pseudonymMode } = usePseudonym()
  // An item to open on, for arriving here from somewhere that was already
  // looking at one — the curate table, say.
  const [searchParams] = useSearchParams()
  const openOnUid = searchParams.get('openItem') ?? undefined
  const [selectedUid, setSelectedUid] = useState<string | undefined>(openOnUid)
  const [tabIndex, setTabIndex] = useState(0)
  const [queueOpen, setQueueOpen] = useState(true)
  // Flagged to start with, since that is what a reviewer was called in for.
  // The other statuses are there to go back to something already dealt with,
  // or to pick out something nobody flagged. Arriving on a named item, no
  // filter: it was asked for by name, and a filter that hides it would leave
  // the view somewhere else entirely.
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | undefined>(
    openOnUid !== undefined ? undefined : ReviewStatus.Flagged,
  )
  // Which kind of item to work through, where more than one is reviewed.
  // Undefined is all of them.
  const [typeFilter, setTypeFilter] = useState<string>()
  const [sortBy, setSortBy] = useState(Sort.Identifier)
  // The overviews own the edits; this is only what the save and revert buttons
  // need to be drawn up here beside the rest of the review commands. One entry
  // per panel that can be edited, since a tab can hold more than one.
  const [editStates, setEditStates] = useState<Record<string, OverviewEditState>>({})
  // One panel for the whole view rather than one per tab: an item opened from
  // the case beside the tab and an item opened from the tab itself are the
  // same gesture, and two panels would be two places to look.
  const dock = useDetailDock(project.uid)

  // Nothing says a schema is the only one reviewed: a project can hand out
  // cases and, say, whole slide images to different reviewers.
  const reviewSchemas = useMemo(
    () =>
      [
        ...Object.values(rootSchema.samples),
        ...Object.values(rootSchema.images),
        ...Object.values(rootSchema.observations),
        ...Object.values(rootSchema.annotations),
      ]
        .filter((schema) => schema.reviewUnit)
        .sort((a, b) => a.displayName.localeCompare(b.displayName)),
    [rootSchema],
  )

  const queuedSchemas = reviewSchemas.filter(
    (schema) => typeFilter === undefined || schema.uid === typeFilter,
  )

  // A queue per kind reviewed, gathered into one: the endpoint answers for a
  // single schema, and which kind an entry is is what was asked for rather
  // than something to read back off it.
  const queueQueries = useQueries({
    queries: queuedSchemas.map((schema) => ({
      queryKey: queryKeys.item.reviewQueue(
        schema.uid,
        project.datasetUid,
        batch.uid,
        statusFilter ?? null,
      ),
      queryFn: async () => {
        const items = await itemApi.getReviewQueue(
          schema.uid,
          project.datasetUid,
          batch.uid,
          statusFilter,
        )
        return items.map((item) => ({ ...item, schemaUid: schema.uid }))
      },
    })),
    combine: (results) => ({
      items: results.flatMap((result) => result.data ?? []),
      isLoading: results.some((result) => result.isLoading),
    }),
  })

  // Last saved first when sorting on it, and never-saved items last: the point
  // of that order is to get back to what was worked on, and an item nobody has
  // touched is the furthest thing from it.
  const queue = useMemo(() => {
    const items = [...queueQueries.items]
    if (sortBy === Sort.Identifier) {
      return items.sort((a, b) => a.identifier.localeCompare(b.identifier))
    }
    return items.sort((a, b) => (b.lastSaved ?? '').localeCompare(a.lastSaved ?? ''))
  }, [queueQueries.items, sortBy])

  /** What the reviewer is shown of an item of this schema, tab by tab, as the
   * schema lays it out. A model that says nothing gets a tab per layout it
   * defined, so an application gains the view without having to describe it
   * first. */
  const tabsFor = useCallback(
    (schemaUid: string | undefined): ReviewTabLayout[] => {
      const declared = rootSchema.reviewLayouts.find(
        (candidate) => candidate.schemaUid === schemaUid,
      )
      if (declared !== undefined) {
        return declared.tabs
      }
      return [
        ...rootSchema.overviewLayouts
          .filter((layout) => layout.schemaUid === schemaUid)
          .map((layout) => ({
            displayName: null,
            panels: [{ kind: 'overview' as const, layout, width: null }],
          })),
        ...rootSchema.hierarchyLayouts
          .filter((layout) => layout.schemaUid === schemaUid)
          .map((layout) => ({
            displayName: null,
            panels: [{ kind: 'hierarchy' as const, layout, width: null }],
          })),
      ]
    },
    [rootSchema],
  )

  /** What to call a tab: what it was named, or what its first panel shows. */
  const tabLabel = useCallback((tab: ReviewTabLayout): string => {
    if (tab.displayName !== null) {
      return tab.displayName
    }
    const panel = tab.panels[0]
    if (panel === undefined || panel.kind === 'images') {
      return 'Images'
    }
    return panel.layout.displayName
  }, [])

  // One callback per panel, kept: a panel reports its edit state from an
  // effect that watches the callback, so handing it a new one every render
  // would have the report cause the render that causes the next report.
  const editReporters = useMemo(
    () => new Map<string, (state: OverviewEditState) => void>(),
    [],
  )
  const editReporter = (key: string): ((state: OverviewEditState) => void) => {
    const known = editReporters.get(key)
    if (known !== undefined) {
      return known
    }
    const reporter = (state: OverviewEditState): void => {
      setEditStates((previous) => ({ ...previous, [key]: state }))
    }
    editReporters.set(key, reporter)
    return reporter
  }

  // Only the panels of the tab being shown: the others are unmounted, and what
  // they last reported says nothing about what is on screen.
  const edits = Object.entries(editStates)
    .filter(([key]) => key.startsWith(`${tabIndex}:`))
    .map(([, state]) => state)
  const isDirty = edits.some((state) => state.isDirty)
  const saving = edits.some((state) => state.saving)

  // Falls back to the first rather than to nothing: a reviewed item leaves the
  // queue, and landing on the top of what is left beats landing on an empty
  // view.
  const index = queue.findIndex((reference) => reference.uid === selectedUid)
  const current = index === -1 ? queue[0] : queue[index]

  // Of whatever is being reviewed right now: a queue holding more than one
  // kind of item is shown by whichever layout that kind has.
  const tabs = tabsFor(current?.schemaUid)
  // Kept in range when stepping from one kind to another, which need not have
  // the same tabs.
  const shownTabIndex = Math.min(tabIndex, Math.max(tabs.length - 1, 0))
  const tab = tabs[shownTabIndex]

  // Dropped with the item rather than left to be written over: the panels of
  // the next item report as they mount, but an item whose tabs hold no
  // editable panel reports nothing, and the buttons would go on offering to
  // save what the last one had.
  useEffect(() => {
    setEditStates({})
  }, [current?.uid])

  const flagInvalidMutation = useMutation({
    mutationFn: async () => await itemApi.flagInvalid(project.datasetUid, batch.uid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })

  const reviewMutation = useMutation({
    mutationFn: async ({
      itemUid,
      status,
    }: {
      itemUid: string
      status: ReviewStatus
    }) => await itemApi.setReviewStatus(itemUid, status),
    onSuccess: () => {
      // What was just acted on leaves a filtered queue, so step on before it
      // does — otherwise the view falls back to the top of the list.
      const position = index === -1 ? 0 : index
      if (statusFilter !== undefined) {
        setSelectedUid(queue[position + 1]?.uid ?? queue[position - 1]?.uid)
      }
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })

  const step = useCallback(
    (offset: number) => {
      const next = queue[(index === -1 ? 0 : index) + offset]
      if (next !== undefined) {
        setSelectedUid(next.uid)
      }
    },
    [queue, index],
  )

  // The same keys the overview binds for stepping and saving, so that working
  // through a queue does not need a different hand: Ctrl+, and Ctrl+. step,
  // Ctrl+Enter acts on the case. Ctrl+S and Ctrl+Z stay with the overview,
  // which owns the edits.
  const { mutate: setReviewStatus } = reviewMutation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (!event.ctrlKey) {
        return
      }
      if (event.key === ',') {
        event.preventDefault()
        step(-1)
      } else if (event.key === '.') {
        event.preventDefault()
        step(1)
      } else if (event.key === 'Enter' && current !== undefined) {
        event.preventDefault()
        setReviewStatus({
          itemUid: current.uid,
          status:
            current.reviewStatus === ReviewStatus.Flagged
              ? ReviewStatus.Reviewed
              : ReviewStatus.Flagged,
        })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [step, current, setReviewStatus])

  if (reviewSchemas.length === 0) {
    return (
      <Typography sx={{ p: 2 }}>No schema is defined as a unit for review.</Typography>
    )
  }
  if (queueQueries.isLoading) {
    return <LinearProgress />
  }

  return (
    // Below the app bar and the padding of the main area, so that the queue and
    // the overview scroll on their own instead of the page growing.
    <Box sx={{ display: 'flex', height: 'calc(100vh - 80px)', gap: 1 }}>
      <Box
        sx={{
          width: queueOpen ? 220 : 40,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          borderRight: 1,
          borderColor: 'divider',
        }}
      >
        <Stack direction="row" sx={{ alignItems: 'center', pl: queueOpen ? 1 : 0 }}>
          {queueOpen && (
            <>
              {/* Named after what is in it where that is one thing, since a
                  reviewer works through cases or slides, not "items". */}
              <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                {queue.length}{' '}
                {queuedSchemas.length === 1
                  ? queueLabel(queuedSchemas[0].displayName, queue.length)
                  : queue.length === 1
                    ? 'item'
                    : 'items'}
              </Typography>
              <Tooltip
                title={
                  sortBy === Sort.Identifier
                    ? 'Sorted by identifier — sort by last saved'
                    : 'Sorted by last saved — sort by identifier'
                }
              >
                <IconButton
                  size="small"
                  onClick={() =>
                    setSortBy(
                      sortBy === Sort.Identifier ? Sort.LastSaved : Sort.Identifier,
                    )
                  }
                >
                  {sortBy === Sort.Identifier ? <SortByAlpha /> : <History />}
                </IconButton>
              </Tooltip>
              <Tooltip title="Flag everything holding an invalid item for review">
                <span>
                  <IconButton
                    size="small"
                    disabled={flagInvalidMutation.isPending}
                    onClick={() => flagInvalidMutation.mutate()}
                  >
                    <Rule />
                  </IconButton>
                </span>
              </Tooltip>
            </>
          )}
          <IconButton size="small" onClick={() => setQueueOpen(!queueOpen)}>
            {queueOpen ? <ChevronLeft /> : <ChevronRight />}
          </IconButton>
        </Stack>
        {queueOpen && (
          <>
            {/* Only where there is a choice to make: one kind reviewed needs no
                control saying so. */}
            {reviewSchemas.length > 1 && (
              <TextField
                select
                size="small"
                value={typeFilter ?? ALL_TYPES}
                onChange={(event) =>
                  setTypeFilter(
                    event.target.value === ALL_TYPES ? undefined : event.target.value,
                  )
                }
                sx={{ mx: 1, mb: 1 }}
              >
                <MenuItem value={ALL_TYPES}>All types</MenuItem>
                {reviewSchemas.map((schema) => (
                  <MenuItem key={schema.uid} value={schema.uid}>
                    {schema.displayName}
                  </MenuItem>
                ))}
              </TextField>
            )}
            <TextField
              select
              size="small"
              value={statusFilter ?? ALL_STATUSES}
              onChange={(event) =>
                setStatusFilter(
                  event.target.value === ALL_STATUSES
                    ? undefined
                    : (event.target.value as ReviewStatus),
                )
              }
              sx={{ mx: 1, mb: 1 }}
            >
              <MenuItem value={ALL_STATUSES}>All</MenuItem>
              {Object.values(ReviewStatus).map((status) => (
                <MenuItem key={status} value={status}>
                  {ReviewStatusStrings[status]}
                </MenuItem>
              ))}
            </TextField>
            <List dense sx={{ overflowY: 'auto', flexGrow: 1 }}>
              {queue.map((item) => (
                <Tooltip
                  key={item.uid}
                  title={
                    item.reviewReason ??
                    (item.reviewStatus === ReviewStatus.Flagged
                      ? 'Flagged without a reason — someone asked for a second pair of eyes.'
                      : ReviewStatusStrings[item.reviewStatus])
                  }
                  placement="right"
                >
                  <ListItemButton
                    selected={item.uid === current?.uid}
                    onClick={() => setSelectedUid(item.uid)}
                  >
                    <ListItemText
                      primary={getDisplayIdentifier(item, pseudonymMode)}
                      // Only what the row cannot be read without: the time when
                      // that is the order, and the kind when the list holds
                      // more than one. Otherwise a line under every row costs
                      // height and answers a question nobody asked.
                      secondary={
                        [
                          queuedSchemas.length > 1
                            ? reviewSchemas.find(
                                (schema) => schema.uid === item.schemaUid,
                              )?.displayName
                            : undefined,
                          sortBy === Sort.LastSaved
                            ? formatSaved(item.lastSaved)
                            : undefined,
                        ]
                          .filter((part) => part !== undefined)
                          .join(' · ') || null
                      }
                      slotProps={{
                        primary: { noWrap: true },
                        secondary: { noWrap: true, variant: 'caption' },
                      }}
                    />
                    {/* Only where the list mixes statuses: a colour repeated
                        down every row of a filtered list says nothing. */}
                    {statusFilter === undefined &&
                      item.reviewStatus !== ReviewStatus.NotReviewed && (
                        <Flag
                          fontSize="small"
                          sx={{
                            color:
                              item.reviewStatus === ReviewStatus.Flagged
                                ? 'error.main'
                                : 'success.main',
                            opacity: 0.7,
                          }}
                        />
                      )}
                  </ListItemButton>
                </Tooltip>
              ))}
            </List>
          </>
        )}
      </Box>
      <Box sx={{ flexGrow: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        {current === undefined ? (
          <Typography sx={{ p: 2 }}>
            {statusFilter === undefined
              ? 'There is nothing here to review.'
              : EMPTY_QUEUE[statusFilter]}
          </Typography>
        ) : (
          <>
            <Stack direction="row" sx={{ alignItems: 'center', gap: 1 }}>
              <Tooltip title="Previous (Ctrl+,)">
                <span>
                  <IconButton
                    size="small"
                    disabled={index <= 0}
                    onClick={() => step(-1)}
                  >
                    <NavigateBefore />
                  </IconButton>
                </span>
              </Tooltip>
              <Typography variant="subtitle1">
                {getDisplayIdentifier(current, pseudonymMode)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {index === -1 ? 1 : index + 1} of {queue.length}
              </Typography>
              <Tooltip title="Next (Ctrl+.)">
                <span>
                  <IconButton
                    size="small"
                    disabled={index === -1 || index >= queue.length - 1}
                    onClick={() => step(1)}
                  >
                    <NavigateNext />
                  </IconButton>
                </span>
              </Tooltip>
              <Box sx={{ flexGrow: 1 }} />
              <Tooltip title="Revert all changes (Ctrl+Z)">
                <span>
                  <IconButton
                    size="small"
                    disabled={!isDirty || saving}
                    onClick={() => edits.forEach((state) => state.revert())}
                  >
                    <Undo />
                  </IconButton>
                </span>
              </Tooltip>
              <Tooltip title="Save all (Ctrl+S)">
                <span>
                  <IconButton
                    size="small"
                    color="primary"
                    disabled={!isDirty || saving}
                    onClick={() => edits.forEach((state) => state.save())}
                  >
                    <Save />
                  </IconButton>
                </span>
              </Tooltip>
              {/* The icon is the action, not the state, and its colour is the
                  state it moves the item into: red to flag, green to mark
                  reviewed. The same rule as in the item details. */}
              <Tooltip
                title={
                  current.reviewStatus === ReviewStatus.Flagged
                    ? current.reviewReason !== null
                      ? `Mark as reviewed (Ctrl+Enter) — flagged: ${current.reviewReason}`
                      : 'Mark as reviewed (Ctrl+Enter)'
                    : 'Flag for review (Ctrl+Enter)'
                }
              >
                <span>
                  <IconButton
                    size="small"
                    disabled={reviewMutation.isPending}
                    onClick={() =>
                      reviewMutation.mutate({
                        itemUid: current.uid,
                        status:
                          current.reviewStatus === ReviewStatus.Flagged
                            ? ReviewStatus.Reviewed
                            : ReviewStatus.Flagged,
                      })
                    }
                  >
                    <Flag
                      sx={{
                        color:
                          current.reviewStatus === ReviewStatus.Flagged
                            ? 'success.main'
                            : 'error.main',
                        opacity: 0.7,
                      }}
                    />
                  </IconButton>
                </span>
              </Tooltip>
            </Stack>
            <Tabs
              value={shownTabIndex}
              onChange={(_, value: number) => setTabIndex(value)}
              variant="scrollable"
            >
              {tabs.map((each, index) => (
                <Tab key={index} label={tabLabel(each)} />
              ))}
            </Tabs>
            <Divider />
            <Box sx={{ flexGrow: 1, minHeight: 0, pt: 1 }}>
              <SplitPanel fillHeight panel={dock.panel}>
                <Box sx={{ height: '100%', minHeight: 0, display: 'flex', gap: 1 }}>
                  {tab === undefined || tab.panels.length === 0 ? (
                    <Typography sx={{ p: 2 }}>
                      Nothing is laid out for reviewing{' '}
                      {reviewSchemas.find((schema) => schema.uid === current.schemaUid)
                        ?.displayName ?? 'this'}
                      .
                    </Typography>
                  ) : (
                    tab.panels.map((panel, panelIndex) => (
                      <Box
                        key={panelIndex}
                        sx={{
                          // What it asked for out of twelve, or an equal share
                          // of what the ones that asked have left.
                          ...(panelWidth(panel) === undefined
                            ? { flex: '1 1 0' }
                            : {
                                width: `${(panelWidth(panel) ?? 0) * (100 / 12)}%`,
                                flexShrink: 0,
                              }),
                          minWidth: 0,
                          height: '100%',
                          minHeight: 0,
                          overflowY: panel.kind === 'overview' ? 'auto' : undefined,
                        }}
                      >
                        {panel.kind === 'images' ? (
                          <ImagesForItem
                            key={`${current.uid}-images-${panelIndex}`}
                            itemUid={current.uid}
                            layout={panel.layout}
                          />
                        ) : panel.kind === 'hierarchy' ? (
                          <HierarchyView
                            key={`${current.uid}-${panel.layout.uid}`}
                            projectUid={project.uid}
                            itemUid={current.uid}
                            layout={panel.layout}
                          />
                        ) : (
                          <OverviewView
                            key={`${current.uid}-${panel.layout.uid}`}
                            projectUid={project.uid}
                            itemUid={current.uid}
                            batchUid={batch.uid}
                            overviewLayout={panel.layout}
                            hideHeader
                            openedItemUid={dock.openedUid}
                            onOpenItem={dock.open}
                            onEditStateChange={editReporter(
                              `${tabIndex}:${panelIndex}`,
                            )}
                          />
                        )}
                      </Box>
                    ))
                  )}
                </Box>
              </SplitPanel>
            </Box>
          </>
        )}
      </Box>
    </Box>
  )
}
