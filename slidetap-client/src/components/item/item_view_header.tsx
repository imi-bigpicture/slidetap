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

import { ChevronLeft, ChevronRight, Save, Undo } from '@mui/icons-material'
import { Box, Button, Card, Tooltip } from '@mui/material'
import { type ReactElement, type ReactNode } from 'react'
import { ValueActions, type ValueAction } from 'src/components/table/value_actions'

/** What the save and revert buttons need, for a view whose content is edited. */
export interface ItemEditState {
  isDirty: boolean
  saving: boolean
  save: () => void
  revert: () => void
}

interface ItemViewHeaderProps {
  /** What the item is called, as it is to be shown — pseudonym where that is
   * the mode. */
  identifier: string
  /** Opens the item itself, where the view can open one. */
  onOpen?: () => void
  /** Shown in place of opening, to say why it cannot be. */
  actions?: ValueAction[]
  /** Stepping through the items the view was reached from, where it has them. */
  onPrevious?: () => void
  onNext?: () => void
  hasPrevious?: boolean
  hasNext?: boolean
  /** Saving and reverting, for a view that edits. Left out for one that
   * only reads — a tree or a gallery has nothing to save. */
  edit?: ItemEditState
  /** Without the card around it, for a view that frames the bar itself: in the
   * review view the tabs sit directly under it, and a card there is a second
   * edge around the same thing. */
  flat?: boolean
  /** Anything the view alone needs, at the right-hand end. */
  children?: ReactNode
}

/**
 * The bar naming the item a view is of.
 *
 * The same wherever an item is opened — an overview, a tree, a gallery — so
 * that what is on screen is said in one place and in one way. What differs
 * between the views is which of the controls apply, not where the name sits.
 */
export default function ItemViewHeader({
  identifier,
  onOpen,
  actions,
  onPrevious,
  onNext,
  hasPrevious = false,
  hasNext = false,
  edit,
  flat = false,
  children,
}: ItemViewHeaderProps): ReactElement {
  const stepping = onPrevious !== undefined || onNext !== undefined
  const bar = (
    <Box
      sx={{
        // The name is placed against the bar rather than between what sits
        // either side of it: laid out in the flow it would be centred between
        // the two groups of buttons, and drift as one side gains a control.
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        px: 2,
        // Tighter without the card: nothing is being separated from what
        // follows, which is already ruled off from it by its own edge.
        py: flat ? 0.25 : 1,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', minWidth: 80 }}>
        {stepping && (
          <Tooltip title="Previous (Ctrl+,)">
            <span>
              <Button disabled={!hasPrevious} onClick={onPrevious} size="small">
                <ChevronLeft />
              </Button>
            </span>
          </Tooltip>
        )}
      </Box>
      {/* The item's identifier opens and copies the same way it does in a
            table, so the bar is a way into the item as well as its name. */}
      <Box
        sx={{
          position: 'absolute',
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
        }}
      >
        <ValueActions
          value={identifier}
          monospace
          copyable
          copyLabel="Copy identifier"
          onOpen={onOpen}
          actions={actions}
        />
      </Box>
      <Box
        sx={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          minWidth: 120,
          gap: 0.5,
        }}
      >
        {children}
        {edit !== undefined && (
          <>
            <Tooltip title="Revert all changes (Ctrl+Z)">
              <span>
                <Button
                  onClick={edit.revert}
                  size="small"
                  disabled={!edit.isDirty || edit.saving}
                >
                  <Undo />
                </Button>
              </span>
            </Tooltip>
            <Tooltip title="Save all (Ctrl+S)">
              <span>
                <Button
                  onClick={edit.save}
                  size="small"
                  disabled={!edit.isDirty || edit.saving}
                  color="primary"
                >
                  <Save />
                </Button>
              </span>
            </Tooltip>
          </>
        )}
        {stepping && (
          <Tooltip title="Next (Ctrl+.)">
            <span>
              <Button disabled={!hasNext} onClick={onNext} size="small">
                <ChevronRight />
              </Button>
            </span>
          </Tooltip>
        )}
      </Box>
    </Box>
  )
  if (flat) {
    return bar
  }
  return (
    // Never gives up height: it is a fixed bar, and what is below it can always
    // scroll instead.
    //
    // Elevation 2 rather than the default: 1 casts almost nothing to the sides,
    // which reads as a bar ruled off at the bottom instead of a card lying on
    // the page. Kept a few pixels off the edges as well — the overview scrolls
    // inside a box of its own, which clips anything drawn outside it, and a bar
    // flush to that edge loses the shadow along its sides.
    <Card elevation={2} sx={{ mx: '4px', mt: '4px', mb: 2, flexShrink: 0 }}>
      {bar}
    </Card>
  )
}
