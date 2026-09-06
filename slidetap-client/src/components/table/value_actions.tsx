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
import {
  Box,
  ClickAwayListener,
  IconButton,
  Link,
  Paper,
  Popper,
  Tooltip,
} from '@mui/material'
import React, { useCallback, useEffect, useRef, useState, type ReactNode } from 'react'
import { Link as RouterLink } from 'react-router-dom'
import { useError } from 'src/contexts/error/error_context'

/** Height of the chip at rest. Matches a medium MUI Chip. */
const CHIP_HEIGHT = 32
/** A chip sized for a row in a list rather than for a page of its own: short
 * enough that the rows stay close together, tall enough that the value in it
 * is not squeezed against its own border. */
const DENSE_CHIP_HEIGHT = 28
/** Waiting before expanding keeps panels from blooming while the pointer runs
 * down a list. Collapsing is quicker but not instant, so moving diagonally onto
 * an entry does not lose it. */
const EXPAND_DELAY_MS = 200
const COLLAPSE_DELAY_MS = 150
const DURATION_MS = 160
/** The icon strip revealed under the identifier: one small IconButton high,
 * each button this wide. Also how far the panel has to unfold, which is what
 * the height it animates to is measured from. */
const TOOLBAR_HEIGHT = 34
const ICON_BUTTON_WIDTH = 32
/** Breathing room kept between an unfolded chip and the window edge. */
const WINDOW_MARGIN = 8

export interface ValueAction {
  key: string
  icon: ReactNode
  label: string
  /** Receives the chip, a stable anchor for any popover the action opens.
   * Left out for an action that only goes somewhere — see `href`. */
  onClick?: (anchor: HTMLElement) => void
  /** Where the action goes, for one that opens a view rather than doing
   * something. Rendered as a link, so a plain click navigates within the
   * application while the browser keeps its own middle-click, ctrl-click and
   * "open in new window". */
  href?: string
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
  /** A shorter chip, for a view showing enough rows at once that their height
   * is what decides how much of the case is in view. */
  dense?: boolean
}

/**
 * The value as a chip that unfolds into its own action panel: a one-line chip
 * at rest, growing on hover (or focus) to reveal copy and the row's actions.
 *
 * The expanded panel is drawn outside the table and placed on the resting chip,
 * head on head, so the value does not move when it opens. It is placed there
 * rather than grown in the cell because the table clips what overflows it, and
 * a chip on the last row would unfold into nothing. With no room below, it
 * flips and unfolds upwards, foot on foot, and the value stays put that way
 * too.
 *
 * The panel follows its row while the table scrolls.
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
  dense = false,
}: ValueActionsProps): React.ReactElement {
  const chipHeight = dense ? DENSE_CHIP_HEIGHT : CHIP_HEIGHT
  const { showError } = useError()
  const restingRef = useRef<HTMLDivElement | null>(null)
  const chipRef = useRef<HTMLDivElement | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const [anchor, setAnchor] = useState<HTMLElement | null>(null)
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

  const openAfterDelay = useCallback(
    (delay: number): void => {
      clearTimer()
      timerRef.current = setTimeout(() => {
        const element = restingRef.current
        if (element === null) return
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
        px: dense ? 1.25 : 1.5,
        height: chipHeight,
        flexShrink: 0,
        // Lets the value below give way when the column is too narrow for it.
        minWidth: 0,
      })}
    >
      {/* Cut to the column at rest. The expanded copy is portalled out of the
          table, where nothing constrains it, so it reads at full length: the
          value is shortened only while there is no room for it. */}
      <Box
        component="span"
        sx={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
      >
        {value}
      </Box>
      {/* Not OpenInNew: that glyph is the "open in new window" action, which
          sits in the same chip. This one opens in place. */}
      {onOpen !== undefined && (
        <ChevronRight fontSize="inherit" sx={{ flexShrink: 0 }} />
      )}
    </Box>
  )

  const chipSx = {
    display: 'flex',
    width: 'max-content',
    border: 1,
    borderColor: quiet ? 'divider' : 'primary.main',
    // Same rounding expanded as at rest: the pill just gets taller.
    borderRadius: `${chipHeight / 2}px`,
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

  return (
    <React.Fragment>
      <Box
        ref={restingRef}
        // Held to the cell so a long value is cut at the column edge rather
        // than run on over the one beside it. `chipSx` is shared with the
        // expanded copy, which is portalled and must not be held to anything.
        sx={{ ...chipSx, flexDirection: 'column', maxWidth: '100%' }}
        onMouseEnter={() => openAfterDelay(EXPAND_DELAY_MS)}
        onMouseLeave={closeAfterDelay}
        onFocus={() => openAfterDelay(0)}
      >
        {openLink}
      </Box>
      <Popper
        open={anchor !== null}
        anchorEl={anchor}
        placement="bottom-start"
        // Placed on the chip rather than beside it: `bottom-start` sets the
        // panel's top-left against the chip's bottom-left, and lifting it by
        // the chip's own height puts the two heads on each other, so the value
        // does not move when the panel opens. Flipped, `top-start` sets the
        // panel's bottom-left against the chip's top-left and the same lift
        // leaves the feet together, which keeps the value still on the way up
        // as well.
        //
        // The panel is left where it is anchored: slid inwards to hold a margin
        // from the window it would read as the value jumping sideways, and a
        // table against the left edge of the page puts the column that most
        // needs to line up inside that margin.
        modifiers={[
          // Lifted by what the chip actually measures, not by the height its
          // value was given: the chip is that height plus its own border, and
          // a lift short by the border leaves the panel sitting low.
          {
            name: 'offset',
            options: {
              offset: ({ reference }: { reference: { height: number } }) => [
                0,
                -reference.height,
              ],
            },
          },
          { name: 'flip', options: { padding: WINDOW_MARGIN } },
          { name: 'preventOverflow', enabled: false },
          // Positioned by plain offsets rather than a rounded transform. The
          // panel has to land on the chip to the pixel, and a transform is
          // snapped to whole device pixels, which on a fractional row offset
          // leaves the two a hair apart.
          {
            name: 'computeStyles',
            options: { gpuAcceleration: false, adaptive: false, roundOffsets: false },
          },
        ]}
        sx={{ zIndex: (theme) => theme.zIndex.modal }}
      >
        {({ placement }) => {
          // Whichever edge is anchored keeps the value still while the panel
          // grows away from it.
          const dropUp = placement.startsWith('top')
          return (
            <ClickAwayListener onClickAway={close}>
              <Paper
                ref={chipRef}
                elevation={expanded ? 3 : 0}
                onMouseEnter={clearTimer}
                onMouseLeave={closeAfterDelay}
                sx={{
                  ...chipSx,
                  flexDirection: dropUp ? 'column-reverse' : 'column',
                  // Wide enough for what unfolds. With only the icon strip that
                  // is usually narrower than the value, so the growth reads as
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
                }}
              >
                {openLink}
                {/* Wrapped together so the pair animates as one, and so a
                    dropUp chip keeps content above the strip rather than
                    reversing it. */}
                <Box className="value-actions-extra" sx={{ overflow: 'hidden' }}>
                  {content !== undefined && (
                    <Box
                      sx={{
                        px: 1.5,
                        pb: 1,
                        maxHeight: contentMaxHeight,
                        overflowY: 'auto',
                      }}
                    >
                      {content}
                    </Box>
                  )}
                  {/* One strip of icon buttons rather than a list of labelled rows:
                  the chip grows by a single line, and the tooltips carry the
                  names so nothing is guessed from a glyph. Omitted entirely
                  when the chip only has content to show. */}
                  {buttonCount > 0 && (
                    <Box
                      sx={{ display: 'flex', alignItems: 'center', px: 0.5, gap: 0.25 }}
                    >
                      {copyable === true && (
                        <Tooltip
                          disableInteractive
                          title={copied ? 'Copied' : copyLabel}
                        >
                          <IconButton size="small" onClick={handleCopy}>
                            <ContentCopy fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      )}
                      {actions?.map((action) => (
                        <Tooltip
                          disableInteractive
                          key={action.key}
                          title={action.label}
                        >
                          {/* Span so the tooltip still shows on a disabled button. */}
                          <span>
                            <IconButton
                              size="small"
                              disabled={action.disabled}
                              // A link where the action is a place: the browser then
                              // offers it the way it offers any link.
                              {...(action.href !== undefined
                                ? { component: RouterLink, to: action.href }
                                : {})}
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
                                  action.onClick?.(anchor)
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
              </Paper>
            </ClickAwayListener>
          )
        }}
      </Popper>
    </React.Fragment>
  )
}
