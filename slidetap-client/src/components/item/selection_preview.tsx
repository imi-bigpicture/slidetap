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

import { Alert, Chip, LinearProgress, Stack, Typography } from '@mui/material'
import type { ReactElement } from 'react'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import {
  CascadeDirection,
  type ItemSelectResult,
  type SelectionChange,
} from 'src/models/item_select'
import type { RootSchema } from 'src/models/schema/root_schema'

/** How many items of a group are named before the rest are counted. */
const SHOWN_PER_GROUP = 8

/** Whether a selection does something a curator should see before it
 * happens: reaches above the item, brings back or leaves out what was taken
 * out by hand, or leaves something in the project short of its schema. */
export function needsConfirmation(result: ItemSelectResult): boolean {
  return (
    result.changed.some(
      (change) => change.direction === CascadeDirection.Up || change.overrodeCuration,
    ) ||
    result.keptOut.length > 0 ||
    result.leftInvalid.length > 0
  )
}

/** Several dry runs, one per item asked for, read as one. */
export function mergeResults(results: ItemSelectResult[]): ItemSelectResult {
  const unique = (changes: SelectionChange[]): SelectionChange[] => [
    ...new Map(changes.map((change) => [change.uid, change])).values(),
  ]
  return {
    changed: unique(results.flatMap((result) => result.changed)),
    keptOut: unique(results.flatMap((result) => result.keptOut)),
    leftInvalid: unique(results.flatMap((result) => result.leftInvalid)),
    dryRun: results.every((result) => result.dryRun),
  }
}

function schemaName(schema: RootSchema, schemaUid: string): string {
  const itemSchema =
    schema.samples[schemaUid] ??
    schema.images[schemaUid] ??
    schema.observations[schemaUid] ??
    schema.annotations[schemaUid]
  return itemSchema?.displayName ?? 'Item'
}

function ChangeGroup({
  title,
  changes,
  color,
}: {
  title: string
  changes: SelectionChange[]
  color: 'default' | 'warning' | 'error'
}): ReactElement | null {
  const schema = useSchemaContext()
  if (changes.length === 0) {
    return null
  }
  const shown = changes.slice(0, SHOWN_PER_GROUP)
  const hidden = changes.length - shown.length
  return (
    <Stack spacing={0.5}>
      <Typography variant="caption" color="text.secondary">
        {title} ({changes.length})
      </Typography>
      <Stack direction="row" spacing={0.5} useFlexGap sx={{ flexWrap: 'wrap' }}>
        {shown.map((change) => (
          <Chip
            key={change.uid}
            size="small"
            color={change.overrodeCuration ? 'warning' : color}
            variant="outlined"
            label={`${schemaName(schema, change.schemaUid)} ${change.identifier}`}
            title={
              change.overrodeCuration
                ? 'Was removed by hand, and will be brought back'
                : ''
            }
          />
        ))}
        {hidden > 0 && <Chip size="small" label={`+${hidden} more`} />}
      </Stack>
    </Stack>
  )
}

interface SelectionPreviewProps {
  /** What the request would do; undefined while it is being worked out. */
  result: ItemSelectResult | undefined
  loading: boolean
  /** Whether the request adds to the project or takes out of it. */
  select: boolean
}

/** What a selection would change, grouped by where it lies from the item. */
export default function SelectionPreview({
  result,
  loading,
  select,
}: SelectionPreviewProps): ReactElement {
  if (loading || result === undefined) {
    return <LinearProgress />
  }
  const verb = select ? 'Restored' : 'Removed'
  const others = result.changed.filter(
    (change) => change.direction !== CascadeDirection.Item,
  )
  const above = others.filter((change) => change.direction === CascadeDirection.Up)
  const below = others.filter((change) => change.direction === CascadeDirection.Down)
  return (
    <Stack spacing={1}>
      {others.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          Nothing else changes.
        </Typography>
      ) : (
        <>
          <ChangeGroup title={`${verb} above it`} changes={above} color="warning" />
          <ChangeGroup title={`${verb} below it`} changes={below} color="default" />
        </>
      )}
      {result.keptOut.length > 0 && (
        <Alert severity="info" variant="outlined" sx={{ py: 0 }}>
          <ChangeGroup
            title="Left out, removed by hand earlier"
            changes={result.keptOut}
            color="default"
          />
        </Alert>
      )}
      {result.leftInvalid.length > 0 && (
        <Alert severity="warning" variant="outlined" sx={{ py: 0 }}>
          <ChangeGroup
            title="Left not valid, to settle before the batch completes"
            changes={result.leftInvalid}
            color="error"
          />
        </Alert>
      )}
    </Stack>
  )
}
