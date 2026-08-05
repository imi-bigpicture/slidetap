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

import { ContentCopy } from '@mui/icons-material'
import { IconButton, Tooltip } from '@mui/material'
import React, { useState } from 'react'
import { useError } from 'src/contexts/error/error_context'

/**
 * Table options putting a "Copy" entry on the cell right-click menu, for the
 * values that have no copy button of their own. Copying uses
 * navigator.clipboard and so needs a secure context (https or localhost).
 */
export const cellCopyOptions = {
  enableCellActions: true,
  enableClickToCopy: 'context-menu',
} as const

interface CopyValueButtonProps {
  value: string
  label: string
}

/** Copy button for a value that gets pasted elsewhere, such as an identifier
 * going into LIS/PACS search. */
export function CopyValueButton({
  value,
  label,
}: CopyValueButtonProps): React.ReactElement {
  const { showError } = useError()
  const [copied, setCopied] = useState(false)
  return (
    <Tooltip title={copied ? 'Copied' : label}>
      <IconButton
        size="small"
        onClick={() => {
          navigator.clipboard.writeText(value).then(
            () => setCopied(true),
            (error) => showError('Failed to copy to clipboard', error),
          )
        }}
        onMouseLeave={() => setCopied(false)}
      >
        <ContentCopy fontSize="inherit" />
      </IconButton>
    </Tooltip>
  )
}
