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

import type { Breakpoint } from 'src/models/schema/attribute_schema'

/** Widths at which a container earns each named breakpoint. Not the theme's
 * breakpoints, which measure the window: a card half a wide window across has
 * the room of a narrow one, and it is the room that decides how many columns
 * fit. */
const containerBreakpoints: Record<string, number> = {
  sm: 400,
  md: 600,
  lg: 800,
  xl: 1024,
}

/**
 * Grid placement for something laid out in twelfths of its container.
 *
 * Turns a width per breakpoint into a `grid-column` span plus a container
 * query for each wider breakpoint, so the item reflows with the box it is in
 * rather than with the window. The grid it is placed in has to declare twelve
 * columns and `container-type: inline-size`.
 *
 * @param width Columns out of twelve, per breakpoint. `xs` defaults to the
 *   full twelve.
 * @param expand The item takes the whole row whatever the widths say.
 *
 * @example
 * // Half the container normally, a third once there is room for it.
 * getContainerSpanSx({ xs: 6, md: 4 }, false)
 */
export const getContainerSpanSx = (
  width: Partial<Record<Breakpoint, number>>,
  expand: boolean,
): Record<string, any> => {
  if (expand) {
    return { gridColumn: '1 / -1' }
  }
  const sx: Record<string, any> = {
    gridColumn: `span ${width.xs ?? 12}`,
  }
  for (const [breakpoint, span] of Object.entries(width)) {
    if (breakpoint === 'xs') continue
    const minWidth = containerBreakpoints[breakpoint]
    if (minWidth !== undefined) {
      sx[`@container (min-width: ${minWidth}px)`] = {
        gridColumn: `span ${span}`,
      }
    }
  }
  return sx
}
