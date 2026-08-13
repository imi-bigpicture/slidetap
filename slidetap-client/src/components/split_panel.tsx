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

import { Box } from '@mui/material'
import React, { useCallback, useRef, useState } from 'react'

interface SplitPanelProps {
  /** Content of the side panel. The panel is hidden when not set. */
  panel?: React.ReactNode
  /** Width of the side panel in pixels before it is dragged. */
  initialWidth?: number
  /** Content filling the remaining width. */
  children: React.ReactNode
  /** Take the height of whatever contains it rather than of its content, so
   * content that bounds its own scrolling has a height to bound against. */
  fillHeight?: boolean
}

/** Main content with a side panel that can be resized by dragging its edge. */
export default function SplitPanel({
  panel,
  initialWidth = 500,
  children,
  fillHeight = false,
}: SplitPanelProps): React.ReactElement {
  const [panelWidth, setPanelWidth] = useState(initialWidth)
  const isResizing = useRef(false)

  const handleResizeStart = useCallback(
    (event: React.MouseEvent) => {
      event.preventDefault()
      isResizing.current = true
      const startX = event.clientX
      const startWidth = panelWidth

      const handleMouseMove = (e: MouseEvent) => {
        if (!isResizing.current) return
        const newWidth = startWidth - (e.clientX - startX)
        setPanelWidth(Math.max(300, Math.min(newWidth, window.innerWidth - 300)))
      }

      const handleMouseUp = () => {
        isResizing.current = false
        document.removeEventListener('mousemove', handleMouseMove)
        document.removeEventListener('mouseup', handleMouseUp)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }

      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
    },
    [panelWidth],
  )

  return (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: panel ? `minmax(0, 1fr) ${panelWidth}px` : '1fr',
        width: '100%',
        overflow: 'hidden',
        ...(fillHeight && { height: '100%', minHeight: 0 }),
      }}
    >
      <Box sx={{ minWidth: 0, overflow: 'auto', ...(fillHeight && { minHeight: 0 }) }}>
        {children}
      </Box>
      {panel && (
        <Box
          sx={{
            display: 'flex',
            minWidth: 0,
            overflow: 'hidden',
            ...(fillHeight && { minHeight: 0 }),
          }}
        >
          {/* A rule between the two, grabbable either side of it: drawn as a
              bar it reads as a scrollbar, which is the one thing a full-height
              grey rounded strip already means. */}
          <Box
            onMouseDown={handleResizeStart}
            sx={{
              width: 10,
              flexShrink: 0,
              cursor: 'col-resize',
              display: 'flex',
              justifyContent: 'center',
              '&:hover > *, &:active > *': {
                width: '2px',
                backgroundColor: 'primary.main',
              },
            }}
          >
            <Box
              sx={{
                width: '1px',
                backgroundColor: 'divider',
                transition: (theme) =>
                  theme.transitions.create(['width', 'background-color'], {
                    duration: 120,
                  }),
              }}
            />
          </Box>
          <Box sx={{ flexGrow: 1, minWidth: 0, overflow: 'auto' }}>{panel}</Box>
        </Box>
      )}
    </Box>
  )
}
