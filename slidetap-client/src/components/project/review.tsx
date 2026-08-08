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
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactElement } from 'react'
import HierarchyView from 'src/components/hierarchy/hierarchy_view'
import OverviewPanel from 'src/components/overview/overview_panel'
import type { OverviewEditState } from 'src/components/overview/overview_view'
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
 * Each tab is one overview layout defined for the review unit schema, so what
 * a reviewer is shown is a schema decision, not a component.
 */
export default function Review({ project, batch }: ReviewProps): ReactElement {
  const rootSchema = useSchemaContext()
  const queryClient = useQueryClient()
  const { pseudonymMode } = usePseudonym()
  const [selectedUid, setSelectedUid] = useState<string>()
  const [tabIndex, setTabIndex] = useState(0)
  const [queueOpen, setQueueOpen] = useState(true)
  // Flagged to start with, since that is what a reviewer was called in for.
  // The other statuses are there to go back to something already dealt with,
  // or to pick out something nobody flagged.
  const [statusFilter, setStatusFilter] = useState<ReviewStatus | undefined>(
    ReviewStatus.Flagged,
  )
  const [sortBy, setSortBy] = useState(Sort.Identifier)
  // The overview owns the edits; this is only what its save and revert buttons
  // need to be drawn up here beside the rest of the review commands.
  const [editState, setEditState] = useState<OverviewEditState>()

  const reviewSchema = useMemo(
    () =>
      [
        ...Object.values(rootSchema.samples),
        ...Object.values(rootSchema.images),
        ...Object.values(rootSchema.observations),
        ...Object.values(rootSchema.annotations),
      ].find((schema) => schema.reviewUnit),
    [rootSchema],
  )

  const queueQuery = useQuery({
    queryKey: queryKeys.item.reviewQueue(
      reviewSchema?.uid ?? '',
      project.datasetUid,
      batch.uid,
      statusFilter ?? null,
    ),
    queryFn: async () => {
      if (reviewSchema === undefined) {
        return []
      }
      return await itemApi.getReviewQueue(
        reviewSchema.uid,
        project.datasetUid,
        batch.uid,
        statusFilter,
      )
    },
    enabled: reviewSchema !== undefined,
  })

  // Last saved first when sorting on it, and never-saved items last: the point
  // of that order is to get back to what was worked on, and an item nobody has
  // touched is the furthest thing from it.
  const queue = useMemo(() => {
    const items = [...(queueQuery.data ?? [])]
    if (sortBy === Sort.Identifier) {
      return items.sort((a, b) => a.identifier.localeCompare(b.identifier))
    }
    return items.sort((a, b) => (b.lastSaved ?? '').localeCompare(a.lastSaved ?? ''))
  }, [queueQuery.data, sortBy])

  const layouts = useMemo(
    () =>
      rootSchema.overviewLayouts.filter(
        (layout) => layout.schemaUid === reviewSchema?.uid,
      ),
    [rootSchema, reviewSchema],
  )

  // Tabs after the overviews: what an item says is read before what it is made
  // of. Both are schema decisions, so a tab is a layout rather than a
  // component.
  const hierarchyLayouts = useMemo(
    () =>
      rootSchema.hierarchyLayouts.filter(
        (layout) => layout.schemaUid === reviewSchema?.uid,
      ),
    [rootSchema, reviewSchema],
  )

  // Falls back to the first rather than to nothing: a reviewed item leaves the
  // queue, and landing on the top of what is left beats landing on an empty
  // view.
  const index = queue.findIndex((reference) => reference.uid === selectedUid)
  const current = index === -1 ? queue[0] : queue[index]

  const flagInvalidMutation = useMutation({
    mutationFn: async () => await itemApi.flagInvalid(project.datasetUid, batch.uid),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
    },
  })

  const reviewMutation = useMutation({
    mutationFn: async ({ itemUid, status }: { itemUid: string; status: ReviewStatus }) =>
      await itemApi.setReviewStatus(itemUid, status),
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

  if (reviewSchema === undefined) {
    return (
      <Typography sx={{ p: 2 }}>No schema is defined as a unit for review.</Typography>
    )
  }
  if (queueQuery.isLoading) {
    return <LinearProgress />
  }

  const layout = layouts[tabIndex]
  const hierarchyLayout = hierarchyLayouts[tabIndex - layouts.length]
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
              <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                {queue.length} {queue.length === 1 ? 'case' : 'cases'}
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
                      // Only when that is what the list is ordered by: a time
                      // under every row otherwise costs height and answers a
                      // question nobody asked.
                      secondary={
                        sortBy === Sort.LastSaved ? formatSaved(item.lastSaved) : null
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
                  <IconButton size="small" disabled={index <= 0} onClick={() => step(-1)}>
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
                    disabled={editState?.isDirty !== true || editState.saving}
                    onClick={() => editState?.revert()}
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
                    disabled={editState?.isDirty !== true || editState.saving}
                    onClick={() => editState?.save()}
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
              value={tabIndex}
              onChange={(_, value: number) => setTabIndex(value)}
              variant="scrollable"
            >
              {layouts.map((each) => (
                <Tab key={each.uid} label={each.displayName} />
              ))}
              {hierarchyLayouts.map((each) => (
                <Tab key={each.uid} label={each.displayName} />
              ))}
            </Tabs>
            <Divider />
            <Box sx={{ flexGrow: 1, minHeight: 0, pt: 1 }}>
              {hierarchyLayout !== undefined ? (
                <HierarchyView
                  key={`${current.uid}-${hierarchyLayout.uid}`}
                  projectUid={project.uid}
                  itemUid={current.uid}
                  layout={hierarchyLayout}
                />
              ) : layout === undefined ? (
                <Typography sx={{ p: 2 }}>
                  No overview layout is defined for {reviewSchema.displayName}.
                </Typography>
              ) : (
                <OverviewPanel
                  key={`${current.uid}-${layout.uid}`}
                  projectUid={project.uid}
                  itemUid={current.uid}
                  overviewLayout={layout}
                  batchUid={batch.uid}
                  hideHeader
                  onEditStateChange={setEditState}
                />
              )}
            </Box>
          </>
        )}
      </Box>
    </Box>
  )
}
