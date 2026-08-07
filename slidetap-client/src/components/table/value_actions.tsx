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

import { ChevronRight, ContentCopy } from '@mui/icons-material'
import { Box, IconButton, Link, Popover, Tooltip } from '@mui/material'
import type { MRT_ColumnDef, MRT_Row, MRT_RowData } from 'material-react-table'
import React, { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { useError } from 'src/contexts/error/error_context'

/** Height of the chip at rest. Matches a medium MUI Chip. */
const CHIP_HEIGHT = 32
/** Waiting before expanding keeps panels from blooming while the pointer runs
 * down a list. Collapsing is quicker but not instant, so moving diagonally onto
 * an entry does not lose it. */
const EXPAND_DELAY_MS = 200
const COLLAPSE_DELAY_MS = 150
const DURATION_MS = 160
/** The icon strip revealed under the identifier: one small IconButton high,
 * each button this wide. Also what decides whether the chip has room to unfold
 * downwards. */
const TOOLBAR_HEIGHT = 34
const ICON_BUTTON_WIDTH = 32
/** Breathing room kept between an unfolded chip and the window edge. */
const WINDOW_MARGIN = 8
/** Marks the panel region that may be scrolled without dismissing the panel. */
const SCROLLABLE_ATTRIBUTE = 'data-value-actions-scrollable'

export interface ValueAction {
  key: string
  icon: ReactNode
  label: string
  /** Receives the chip, a stable anchor for any popover the action opens. */
  onClick: (anchor: HTMLElement) => void
  disabled?: boolean
  /** Keep the panel open after this is clicked, until something outside it is
   * clicked. For actions that open a popover of their own: the panel is
   * hover-driven, so it would otherwise vanish the moment the pointer moved
   * towards what it just opened. */
  pin?: boolean
}

interface ValueActionsProps {
  value: string
  /** Identifiers are codes that get scanned and pasted, so they read better in
   * monospace than the prose names in the other tables. */
  monospace?: boolean
  onOpen?: () => void
  /** Only for values that get pasted elsewhere — an identifier going into
   * LIS/PACS search. Everything else is served well enough by the cell's
   * right-click Copy. */
  copyable?: boolean
  copyLabel?: string
  actions?: ValueAction[]
  /** Shown above the icon strip when expanded — the attribute's details, the
   * related items, whatever the cell has more to say. Scrolls past
   * `contentMaxHeight`. */
  content?: ReactNode
  contentMaxHeight?: number
  contentMinWidth?: number
  /** The identifier chip is the way into the row and says so in primary; value
   * chips are quieter. */
  quiet?: boolean
}

/**
 * The value as a chip that unfolds into its own action panel: a one-line chip
 * at rest, growing on hover (or focus) to reveal copy and the row's actions.
 *
 * The expanded chip is a Popover anchored to the resting one, top-left to
 * top-left, so its head lands on the resting head and the value does not move.
 * Expanding in place instead would grow MRT's scroll container, shifting the
 * table and clipping the chip on the last rows. Near the bottom of the window
 * it anchors bottom-to-bottom and reverses, so the value still stays put while
 * the panel unfolds upwards.
 */
export function ValueActions({
  value,
  monospace,
  onOpen,
  copyable,
  copyLabel = 'Copy',
  actions,
  content,
  contentMaxHeight = 320,
  contentMinWidth = 320,
  quiet,
}: ValueActionsProps): React.ReactElement {
  const { showError } = useError()
  const restingRef = useRef<HTMLDivElement | null>(null)
  const chipRef = useRef<HTMLDivElement | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const suppressedRef = useRef(false)
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)
  const [dropUp, setDropUp] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [copied, setCopied] = useState(false)
  const [pinned, setPinned] = useState(false)

  const clearTimer = useCallback((): void => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const close = useCallback((): void => {
    clearTimer()
    setAnchor(null)
    setExpanded(false)
    setCopied(false)
    setPinned(false)
  }, [clearTimer])

  /** Rows sliding under a still pointer re-fire mouseenter, which would reopen
   * the panel the scroll just dismissed, over and over. Wait for the pointer to
   * actually move before hovering counts again. */
  const suppressReopen = useCallback((): void => {
    if (suppressedRef.current) return
    suppressedRef.current = true
    const release = (): void => {
      suppressedRef.current = false
      window.removeEventListener('pointermove', release)
    }
    window.addEventListener('pointermove', release)
  }, [])

  const openAfterDelay = useCallback(
    (delay: number, expandedHeight: number): void => {
      if (suppressedRef.current) return
      clearTimer()
      timerRef.current = setTimeout(() => {
        const element = restingRef.current
        if (element === null) return
        const rect = element.getBoundingClientRect()
        // Unfold upwards only when the panel would be cut off by the window.
        // Hanging past the table is fine.
        setDropUp(rect.bottom + expandedHeight > window.innerHeight - WINDOW_MARGIN)
        setAnchor(element)
        // Expand on the next frame so the transition has a collapsed state to
        // start from.
        requestAnimationFrame(() => setExpanded(true))
      }, delay)
    },
    [clearTimer],
  )

  const closeAfterDelay = useCallback((): void => {
    // Pinned: something the panel opened is still on screen, and the pointer
    // has to leave the panel to reach it.
    if (pinned) return
    clearTimer()
    timerRef.current = setTimeout(close, COLLAPSE_DELAY_MS)
  }, [clearTimer, close, pinned])

  // Popover anchors once and does not follow the table, so a scroll leaves the
  // panel stranded — unless the scroll is inside the panel itself, which is how
  // long attribute content is read. Wheel and touch are listened for as well as
  // scroll: a table too short to scroll still bounces under the gesture, moving
  // the rows without ever firing a scroll event.
  useEffect(() => {
    if (anchor === null) return
    const closeOnOutsideScroll = (event: Event): void => {
      // Exempt only content that has somewhere to scroll. The panel covers the
      // chip, so the pointer is usually over the panel itself — exempting all
      // of it would leave the panel stuck open through any scroll.
      const scrollable = (event.target as HTMLElement | null)?.closest?.(
        `[${SCROLLABLE_ATTRIBUTE}]`,
      )
      if (scrollable != null && scrollable.scrollHeight > scrollable.clientHeight) {
        return
      }
      close()
      suppressReopen()
    }
    const options = { capture: true, passive: true }
    window.addEventListener('scroll', closeOnOutsideScroll, options)
    window.addEventListener('wheel', closeOnOutsideScroll, options)
    window.addEventListener('touchmove', closeOnOutsideScroll, options)
    return () => {
      window.removeEventListener('scroll', closeOnOutsideScroll, true)
      window.removeEventListener('wheel', closeOnOutsideScroll, true)
      window.removeEventListener('touchmove', closeOnOutsideScroll, true)
    }
  }, [anchor, close])

  useEffect(() => clearTimer, [clearTimer])

  const handleCopy = (): void => {
    navigator.clipboard.writeText(value).then(
      () => setCopied(true),
      (error) => showError('Failed to copy to clipboard', error),
    )
  }

  const head = (
    <Box
      sx={(theme) => ({
        // Stated rather than inherited: the expanded copy is portalled out of
        // the table, where `inherit` would pick up the body's 16px instead of
        // the cell's body2.
        ...theme.typography.body2,
        fontFamily: monospace ? 'monospace' : undefined,
        fontWeight: 500,
        display: 'flex',
        alignItems: 'center',
        gap: 0.5,
        px: 1.5,
        height: CHIP_HEIGHT,
        flexShrink: 0,
      })}
    >
      {value}
      {/* Not OpenInNew: that glyph is the "open in new window" action, which
          sits in the same chip. This one opens in place. */}
      {onOpen !== undefined && <ChevronRight fontSize="inherit" />}
    </Box>
  )

  const chipSx = {
    display: 'flex',
    width: 'max-content',
    border: 1,
    borderColor: quiet ? 'divider' : 'primary.main',
    // Same rounding expanded as at rest: the pill just gets taller.
    borderRadius: `${CHIP_HEIGHT / 2}px`,
    backgroundColor: 'background.paper',
    color: quiet ? 'text.primary' : 'primary.main',
  } as const

  const openLink = (
    <Link
      component="button"
      underline="hover"
      disabled={onOpen === undefined}
      onClick={onOpen}
      sx={{ color: 'inherit', textAlign: 'left', p: 0 }}
    >
      {head}
    </Link>
  )

  const buttonCount = (actions?.length ?? 0) + (copyable === true ? 1 : 0)
  const toolbarWidth = buttonCount * ICON_BUTTON_WIDTH + 8

  const expandedHeight =
    (buttonCount > 0 ? TOOLBAR_HEIGHT : 0) +
    (content !== undefined ? contentMaxHeight : 0)
  const expandedWidth = Math.max(
    toolbarWidth,
    content !== undefined ? contentMinWidth : 0,
  )

  // Whichever edge is anchored keeps the value still while the panel grows away
  // from it.
  const edge = dropUp ? 'bottom' : 'top'

  return (
    <React.Fragment>
      <Box
        ref={restingRef}
        sx={{ ...chipSx, flexDirection: 'column' }}
        onMouseEnter={() => openAfterDelay(EXPAND_DELAY_MS, expandedHeight)}
        onMouseLeave={closeAfterDelay}
        onFocus={() => openAfterDelay(0, expandedHeight)}
      >
        {openLink}
      </Box>
      <Popover
        open={anchor !== null}
        anchorEl={anchor}
        onClose={close}
        // The panel's own head lands on the resting one, so the value does not
        // move when it opens.
        anchorOrigin={{ vertical: edge, horizontal: 'left' }}
        transformOrigin={{ vertical: edge, horizontal: 'left' }}
        // Grow would scale the panel out of a point, reading as the value
        // sliding into place; it should just be there, then unfold.
        transitionDuration={0}
        disableScrollLock
        disableAutoFocus
        disableEnforceFocus
        disableRestoreFocus
        // Pinned, the panel needs a backdrop to catch the click that dismisses
        // it; unpinned it must let pointer events through to the table.
        hideBackdrop={!pinned}
        // Hover-driven, so the modal root must not swallow pointer events meant
        // for the table underneath.
        sx={{ pointerEvents: pinned ? 'auto' : 'none' }}
        slotProps={{
          paper: {
            ref: chipRef,
            elevation: expanded ? 3 : 0,
            onMouseEnter: clearTimer,
            onMouseLeave: closeAfterDelay,
            sx: {
              ...chipSx,
              pointerEvents: 'auto',
              flexDirection: dropUp ? 'column-reverse' : 'column',
              // Wide enough for what unfolds. With only the icon strip that is
              // usually narrower than the value, so the growth reads as
              // vertical; content asks for more room.
              minWidth: expanded ? expandedWidth : 0,
              overflow: 'hidden',
              transition: (theme) =>
                theme.transitions.create('min-width', { duration: DURATION_MS }),
              '& .value-actions-extra': {
                maxHeight: expanded ? expandedHeight : 0,
                opacity: expanded ? 1 : 0,
                transition: (theme) =>
                  theme.transitions.create(['max-height', 'opacity'], {
                    duration: DURATION_MS,
                  }),
              },
            },
          },
        }}
      >
            {openLink}
            {/* Wrapped together so the pair animates as one, and so a dropUp
                chip keeps content above the strip rather than reversing it. */}
            <Box className="value-actions-extra" sx={{ overflow: 'hidden' }}>
              {content !== undefined && (
                <Box
                  {...{ [SCROLLABLE_ATTRIBUTE]: true }}
                  sx={{ px: 1.5, pb: 1, maxHeight: contentMaxHeight, overflowY: 'auto' }}
                >
                  {content}
                </Box>
              )}
              {/* One strip of icon buttons rather than a list of labelled rows:
                  the chip grows by a single line, and the tooltips carry the
                  names so nothing is guessed from a glyph. Omitted entirely
                  when the chip only has content to show. */}
              {buttonCount > 0 && (
              <Box sx={{ display: 'flex', alignItems: 'center', px: 0.5, gap: 0.25 }}>
              {copyable === true && (
                <Tooltip title={copied ? 'Copied' : copyLabel}>
                  <IconButton size="small" onClick={handleCopy}>
                    <ContentCopy fontSize="small" />
                  </IconButton>
                </Tooltip>
              )}
              {actions?.map((action) => (
                <Tooltip key={action.key} title={action.label}>
                  {/* Span so the tooltip still shows on a disabled button. */}
                  <span>
                    <IconButton
                      size="small"
                      disabled={action.disabled}
                      onClick={() => {
                        const anchor = chipRef.current
                        // A pinned action opens something of its own, so the
                        // panel stays where it is instead of closing out from
                        // under what it just opened.
                        if (action.pin === true) {
                          setPinned(true)
                        } else {
                          close()
                        }
                        if (anchor !== null) {
                          action.onClick(anchor)
                        }
                      }}
                    >
                      {action.icon}
                    </IconButton>
                  </span>
                </Tooltip>
              ))}
              </Box>
              )}
        </Box>
      </Popover>
    </React.Fragment>
  )
}

/**
 * Put the chip on the first column of a table, leaving the rest untouched.
 *
 * Memoize the result — MRT rebuilds column state when column identity changes.
 */
export function withValueActionsColumn<T extends MRT_RowData>(
  columns: MRT_ColumnDef<T>[],
  getValue: (row: MRT_Row<T>) => string,
  getOpen: (row: MRT_Row<T>) => (() => void) | undefined,
  getActions: (row: MRT_Row<T>) => ValueAction[],
): MRT_ColumnDef<T>[] {
  const [first, ...rest] = columns
  if (first === undefined) {
    return columns
  }
  return [
    {
      ...first,
      Cell: (props) => (
        <ValueActions
          value={getValue(props.row)}
          onOpen={getOpen(props.row)}
          actions={getActions(props.row)}
          copyable
          copyLabel="Copy name"
        />
      ),
    },
    ...rest,
  ]
}
