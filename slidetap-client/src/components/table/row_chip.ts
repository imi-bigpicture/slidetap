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

import type { SxProps, Theme } from '@mui/material'

/**
 * A chip that sits in a table row.
 *
 * Between the two sizes Material offers: `small` packs the value against its
 * own border, and the default is built for a chip standing on its own rather
 * than one of several down a column. Kept in step with the identifier panel's
 * `dense` chip, so every chip in a row is the same height.
 */
export const rowChipSx: SxProps<Theme> = {
  height: 28,
  '& .MuiChip-label': { px: 1.25 },
}
