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

import { Chip, Stack, Typography } from '@mui/material'
import { type ReactElement } from 'react'
import OutlinedFormControl from 'src/components/attribute/outlined_form_control'

export interface SchemaChipEntry {
  /** Identifies the chip, and the schema to open when it is clicked. */
  uid: string
  title: string
}

interface SchemaChipsProps {
  label: string
  entries: SchemaChipEntry[]
  /** Called with the uid of the clicked entry. Chips are not clickable if not set. */
  onClick?: (uid: string) => void
}

/** Display a labelled row of schema values, one chip per entry.
 *
 * An empty row is shown as "None", so that a property the schema has no values
 * for reads as empty rather than as a label with nothing under it. Hide the
 * whole row at the call site for properties that are usually empty.
 */
export default function SchemaChips({
  label,
  entries,
  onClick,
}: SchemaChipsProps): ReactElement {
  return (
    <OutlinedFormControl label={label} fullWidth>
      <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap', rowGap: 0.5 }}>
        {entries.length === 0 ? (
          <Typography variant="body2" sx={{ color: 'text.disabled' }}>
            None
          </Typography>
        ) : (
          entries.map((entry) => (
            <Chip
              key={entry.uid}
              label={entry.title}
              size="small"
              onClick={onClick === undefined ? undefined : () => onClick(entry.uid)}
            />
          ))
        )}
      </Stack>
    </OutlinedFormControl>
  )
}
