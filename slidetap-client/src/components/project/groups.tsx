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
import { Delete, Refresh } from '@mui/icons-material'
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControlLabel,
  LinearProgress,
  Stack,
  Switch,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import SelectionTreeDialog from 'src/components/item/selection_tree_dialog'
import GroupGrid from 'src/components/project/group_grid'
import GroupItems from 'src/components/project/group_items'
import GroupValue from 'src/components/project/group_value'
import {
  GroupStatus,
  STATUS_DISPLAY,
  groupStatus,
} from 'src/components/project/group_status'
import { BasicDataTable } from 'src/components/table/basic_data_table'
import type { ColumnDef } from 'src/components/table/data_table/types'
import { useError } from 'src/contexts/error/error_context'
import { useProjectActions } from 'src/contexts/project_actions/project_actions_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { Action } from 'src/models/action'
import { NIL_UID } from 'src/models/attribute'
import type { Batch } from 'src/models/batch'
import type { ItemGroupSummary } from 'src/models/item_grouping'
import type { Project } from 'src/models/project'
import projectApi from 'src/services/api/project_api'
import tagApi from 'src/services/api/tag_api'
import { queryKeys } from 'src/services/query_keys'

/** The tag given to what is taken out with a group, so that it can be found
 * again in curate, and put back there. */
const REMOVED_TAG_NAME = 'Group too small'

/** As long as the server keeps a comment. */
const MAX_COMMENT_LENGTH = 512

/** Items about to be taken out with the groups they are in, for the dialog
 * that shows what goes with them. */
interface Removal {
  itemUids: string[]
  subject: string
  comment: string
  tagUids: string[]
  /** The groups taken out, by uid: the detail of one of them is closed once
   * it is, rather than told its items fell in other groups. */
  groupUids: string[]
}

interface GroupsProps {
  project: Project
  /** Only the items of this batch, when the batch view is open. */
  batch?: Batch
}

/** A group with the row identity the table needs: what its items share,
 * which no two groups do, and a number to open it by that is none of its
 * values: in the order the server gives, smallest first. */
interface GroupRow extends ItemGroupSummary {
  uid: string
  number: number
}

/** What the side panel lists: the items of a group, or those in none. The
 * group by its uid rather than as it was when opened, so that the panel shows
 * it as the groups now have it. */
type Opened = { kind: 'group'; uid: string } | { kind: 'incomplete' }

/**
 * The groups the items of a project, or of a batch, fall into by what they
 * share, with those holding too few marked.
 *
 * Meant for what could single someone out of a dataset, such as a diagnose,
 * a site and an age bucket: curating can move an item into a group too small,
 * which is what this is to show. Worked out by the server each time it is
 * opened, showing the last result until it is, and when refreshed.
 */
export default function Groups({ project, batch }: GroupsProps): ReactElement {
  const rootSchema = useSchemaContext()
  const [onlyTooSmall, setOnlyTooSmall] = React.useState(true)
  // The list is the view to work from; the grid is the overview beside it.
  const [view, setView] = React.useState<'list' | 'grid'>('list')
  const [opened, setOpened] = React.useState<Opened>()
  // Which kind of item the detail shows, kept from one group to the next.
  const [detailTab, setDetailTab] = React.useState<string>()
  const groupsQuery = useQuery({
    queryKey: queryKeys.project.groups(project.uid, batch?.uid),
    queryFn: async () => await projectApi.getGroups(project.uid, batch?.uid),
    // Worked out again on every visit, as a correction is made on another
    // page, while the last result is shown; not on coming back to the window,
    // as working it out takes a while on a large project. Refresh is there
    // for a correction made in another tab.
    refetchOnMount: 'always',
  })
  /** Brings a group just opened into view, as it opens below the groups. Kept
   * the same between renders, so that it scrolls once per group opened. */
  const scrollIntoView = React.useCallback((node: HTMLDivElement | null): void => {
    node?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }, [])
  const queryClient = useQueryClient()
  const { showError } = useError()
  const { edit: canEdit } = useProjectActions()
  const [removal, setRemoval] = React.useState<Removal | null>(null)
  const [preparingRemoval, setPreparingRemoval] = React.useState(false)

  /** Open the dialog for taking items out, tagged so that they can be found
   * again. The tag is made the first time it is needed. */
  const startRemoval = async (next: Omit<Removal, 'tagUids'>): Promise<void> => {
    setPreparingRemoval(true)
    try {
      const tags = await tagApi.getTags()
      let tag = tags.find((candidate) => candidate.name === REMOVED_TAG_NAME)
      if (tag === undefined) {
        tag = await tagApi.save({
          uid: NIL_UID,
          name: REMOVED_TAG_NAME,
          description: 'Taken out of the project with a group too small to export.',
          color: null,
        })
        void queryClient.invalidateQueries({ queryKey: queryKeys.tag.all })
      }
      setRemoval({
        ...next,
        comment: next.comment.slice(0, MAX_COMMENT_LENGTH),
        tagUids: [tag.uid],
      })
    } catch (error) {
      showError('Failed to prepare removing the group', error)
    } finally {
      setPreparingRemoval(false)
    }
  }

  if (groupsQuery.isLoading) {
    return <LinearProgress />
  }
  if (groupsQuery.isError) {
    // Not told as a project that groups nothing, which would read as there
    // being no size to check.
    return (
      <Alert
        severity="error"
        sx={{ m: 1 }}
        action={
          <Button
            color="inherit"
            size="small"
            onClick={() => void groupsQuery.refetch()}
          >
            Retry
          </Button>
        }
      >
        The groups could not be worked out: {groupsQuery.error.message}
      </Alert>
    )
  }
  const grouping = groupsQuery.data
  if (grouping === undefined || grouping === null) {
    return (
      <Typography sx={{ p: 2 }}>
        The schema of this project does not group its items.
      </Typography>
    )
  }
  const { policy } = grouping
  const itemsName =
    rootSchema.samples[policy.schemaUid]?.displayName ??
    rootSchema.observations[policy.schemaUid]?.displayName ??
    'Items'
  const rows: GroupRow[] = grouping.groups.map((group, index) => ({
    ...group,
    uid: group.values.join('\u0000'),
    number: index + 1,
  }))
  const tooSmall = rows.filter((row) => row.belowMinimum)
  const shown = onlyTooSmall ? tooSmall : rows
  const countName = policy.countDisplayName.toLowerCase()
  const itemsCount = (count: number): string => `${count} ${itemsName.toLowerCase()}`

  /** Take a group's items out, from its detail. Any group, as one close to
   * the minimum may be judged too small too. Taking it out changes no other
   * group: each counts what has an item in it, and what goes with these
   * items goes only once nothing else of it is left. */
  const removeGroup = (row: GroupRow): void => {
    void startRemoval({
      itemUids: row.items.map((item) => item.uid),
      subject: `the ${itemsCount(row.items.length)} of group ${row.number}`,
      comment: `Taken out with group ${row.number}, of ${row.count} ${countName}: ${grouping.columns
        .map((name, index) => `${name}: ${row.values[index]}`)
        .join('; ')}.`,
      groupUids: [row.uid],
    })
  }
  /** Take out every group below the minimum at once. Done in one go, as
   * taking out one of them leaves the others, and the rest, as they were. */
  const removeTooSmall = (): void => {
    const itemUids = tooSmall.flatMap((row) => row.items.map((item) => item.uid))
    void startRemoval({
      itemUids,
      subject: `the ${itemsCount(itemUids.length)} of the ${tooSmall.length} groups with fewer than ${policy.minimumCount} ${countName}`,
      comment: `Taken out with a group of fewer than ${policy.minimumCount} ${countName}.`,
      groupUids: tooSmall.map((row) => row.uid),
    })
  }

  const columns: Array<ColumnDef<GroupRow>> = [
    {
      // First, as the table opens a row from its first column: a group is all
      // of its values, not any one of them.
      id: 'group',
      header: 'Group',
      accessorKey: 'number',
      size: 110,
    },
    ...grouping.columns.map((name, index): ColumnDef<GroupRow> => ({
      id: `value-${index}`,
      header: name,
      accessorFn: (row) => row.values[index] ?? '',
      Cell: ({ row }) => (
        <GroupValue text={row.values[index] ?? ''} parts={row.parts[index]} />
      ),
      filter: { variant: 'text' },
      grow: true,
    })),
    {
      id: 'count',
      header: policy.countDisplayName,
      accessorKey: 'count',
      size: 110,
    },
    {
      id: 'items',
      header: itemsName,
      // Beside what is counted, since several items can be of one of it.
      accessorFn: (row) => row.items.length,
      size: 110,
    },
    {
      id: 'status',
      header: 'Status',
      accessorFn: (row) => groupStatus(row, policy),
      filter: {
        variant: 'select',
        options: Object.values(GroupStatus).map((status) => ({
          label: status,
          value: status,
        })),
      },
      size: 150,
      Cell: ({ row }) => {
        const status = groupStatus(row, policy)
        const display = STATUS_DISPLAY[status]
        return (
          <Chip
            size="small"
            variant="outlined"
            color={display.color}
            icon={display.icon}
            label={status}
          />
        )
      },
    },
  ]

  const reviewUnitSchemaUid = rootSchema.reviewUnit?.schemaUid
  const openedRow =
    opened?.kind === 'group'
      ? rows.find((candidate) => candidate.uid === opened.uid)
      : undefined
  const detail =
    opened === undefined ? null : opened.kind === 'group' && openedRow === undefined ? (
      // A correction has moved every item of the group into others.
      <Alert severity="info" onClose={() => setOpened(undefined)}>
        This group has no items any more: they now fall in other groups.
      </Alert>
    ) : openedRow !== undefined ? (
      <GroupItems
        // A table of its own per group, starting on its first page.
        key={openedRow.uid}
        project={project}
        batch={batch}
        tab={detailTab}
        onTabChange={setDetailTab}
        title={`Group ${openedRow.number}: ${openedRow.count} ${policy.countDisplayName.toLowerCase()}, ${groupStatus(openedRow, policy).toLowerCase()}`}
        details={grouping.columns.map(
          (name, index) => `${name}: ${openedRow.values[index]}`,
        )}
        actions={
          <Button
            size="small"
            color="error"
            startIcon={<Delete />}
            disabled={!canEdit || preparingRemoval}
            onClick={() => removeGroup(openedRow)}
          >
            Remove group
          </Button>
        }
        tabs={[
          {
            schemaUid: policy.schemaUid,
            uids: openedRow.items.map((item) => item.uid),
          },
          ...(reviewUnitSchemaUid !== undefined &&
          reviewUnitSchemaUid !== policy.schemaUid
            ? [{ schemaUid: reviewUnitSchemaUid, uids: openedRow.reviewUnitUids }]
            : []),
        ]}
        onClose={() => setOpened(undefined)}
      />
    ) : (
      <GroupItems
        key="incomplete"
        project={project}
        batch={batch}
        title={`In no group: ${grouping.incomplete.length}`}
        details={[
          'Each lacks a value grouped by, such as one not mapped yet, so it is not valid either.',
          ...[...new Set(grouping.incomplete.flatMap((entry) => entry.missing))].map(
            (missing) =>
              `No ${missing.toLowerCase()}: ${grouping.incomplete.filter((entry) => entry.missing.includes(missing)).length}`,
          ),
        ]}
        tabs={[
          {
            schemaUid: policy.schemaUid,
            uids: grouping.incomplete.map((entry) => entry.item.uid),
          },
        ]}
        onClose={() => setOpened(undefined)}
      />
    )

  return (
    <Box>
      <Stack spacing={1} sx={{ p: 1 }}>
        <Typography variant="body2" color="text.secondary">
          {rows.length} groups, {tooSmall.length} with fewer than {policy.minimumCount}{' '}
          {policy.countDisplayName.toLowerCase()}, and {grouping.incomplete.length}{' '}
          {itemsName.toLowerCase()} in no group, counted in this{' '}
          {batch !== undefined ? 'batch' : 'project'}.
        </Typography>
        <Stack direction="row" spacing={2} sx={{ alignItems: 'center' }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={view}
            onChange={(_, value: 'list' | 'grid' | null) => {
              if (value !== null) setView(value)
            }}
          >
            <ToggleButton value="list">List</ToggleButton>
            <ToggleButton value="grid">Grid</ToggleButton>
          </ToggleButtonGroup>
          <Button
            size="small"
            startIcon={<Refresh />}
            disabled={groupsQuery.isFetching}
            onClick={() => void groupsQuery.refetch()}
          >
            Refresh
          </Button>
          <Typography variant="caption" color="text.secondary">
            {groupsQuery.isFetching
              ? 'Working out the groups again…'
              : `As of ${new Date(groupsQuery.dataUpdatedAt).toLocaleTimeString()}`}
          </Typography>
        </Stack>
        {/* Over the groups rather than in place of them: the last result
            stays to work from while the new one is worked out. */}
        {groupsQuery.isFetching && <LinearProgress />}
        {view === 'grid' ? (
          // Every group, as a gap in a row or a column only shows beside the
          // groups around it.
          <GroupGrid
            grouping={grouping}
            onOpenGroup={(group) =>
              setOpened({ kind: 'group', uid: group.values.join('\u0000') })
            }
          />
        ) : (
          <BasicDataTable
            columns={columns}
            data={shown}
            rowsSelectable={false}
            topBarActions={[
              <FormControlLabel
                key="only-too-small"
                control={
                  <Switch
                    checked={onlyTooSmall}
                    onChange={(event) => setOnlyTooSmall(event.target.checked)}
                  />
                }
                label="Only too small"
              />,
              <Button
                key="incomplete"
                disabled={grouping.incomplete.length === 0}
                onClick={() => setOpened({ kind: 'incomplete' })}
              >
                {grouping.incomplete.length} in no group
              </Button>,
              <Button
                key="remove-too-small"
                color="error"
                startIcon={<Delete />}
                disabled={!canEdit || preparingRemoval || tooSmall.length === 0}
                onClick={removeTooSmall}
              >
                Remove all too small
              </Button>,
            ]}
            actions={[
              {
                action: Action.VIEW,
                onAction: (row) => setOpened({ kind: 'group', uid: row.uid }),
              },
            ]}
          />
        )}
        {detail !== null && (
          // Below the groups rather than beside them: the curate table needs
          // the width, and the group it is of stays in sight above it.
          // Keyed by what is open, so that the box is new for each group, and
          // its ref scrolls each into view rather than only the first.
          <Box
            key={opened?.kind === 'group' ? opened.uid : 'incomplete'}
            ref={scrollIntoView}
          >
            {detail}
          </Box>
        )}
      </Stack>
      {removal !== null && (
        <SelectionTreeDialog
          itemUids={removal.itemUids}
          schemaUids={[policy.schemaUid]}
          // What goes with them shown by kind, as a group is many items.
          byTypeAtStart
          select={false}
          subject={removal.subject}
          comment={removal.comment}
          tags={removal.tagUids}
          additiveTags
          onClose={() => setRemoval(null)}
          onApplied={() => {
            if (opened?.kind === 'group' && removal.groupUids.includes(opened.uid)) {
              setOpened(undefined)
            }
            // What went with the items may be listed anywhere, and the groups
            // of the project and of every batch count them.
            void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
            void queryClient.invalidateQueries({
              queryKey: [...queryKeys.project.detail(project.uid), 'groups'],
            })
          }}
          onError={(error) => showError('Failed to remove the group', error)}
        />
      )}
    </Box>
  )
}
