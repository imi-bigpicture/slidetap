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

import { Chip, Stack, Tooltip, Typography } from '@mui/material'
import { type ReactElement } from 'react'
import type { ItemGroupValuePart } from 'src/models/item_grouping'

interface GroupValueProps {
  /** The value as text, shown where it has no parts. */
  text: string
  /** What the value is made of, each shown as a chip. */
  parts?: ItemGroupValuePart[]
  /** Where the chips line up across the space they are given. */
  justify?: 'flex-start' | 'center'
}

/** A value of a group: a chip for each of what it is made of, such as one per
 * diagnose of a set, with its description, such as the code, on hover. Its
 * text where it is not given in parts. */
export default function GroupValue({
  text,
  parts,
  justify = 'flex-start',
}: GroupValueProps): ReactElement {
  if (parts === undefined || parts.length === 0) {
    return <Typography variant="body2">{text}</Typography>
  }
  return (
    <Stack
      direction="row"
      spacing={0.5}
      useFlexGap
      sx={{ flexWrap: 'wrap', justifyContent: justify }}
    >
      {parts.map((part, index) => (
        <Tooltip key={index} title={part.description ?? ''}>
          <Chip size="small" variant="outlined" label={part.label} />
        </Tooltip>
      ))}
    </Stack>
  )
}
