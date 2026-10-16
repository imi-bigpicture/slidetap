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

import { Chip, Stack, Typography } from '@mui/material'
import type { ReactElement } from 'react'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import type { SelectionChange } from 'src/models/item_select'
import { schemaName } from './schema_name'

/** How many items of a group are named before the rest are counted. */
const SHOWN_PER_GROUP = 8

/** Items a selection changes, or would change, named up to a limit and
 * counted beyond it. */
export function ChangeGroup({
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
