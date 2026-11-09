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

import React from 'react'

/** How the entries of a list are dragged, where whatever shows the list lets
 * them be: each by a handle of its own, onto another entry to swap the two, or
 * past the last to move it there.
 *
 * Given by what knows where the list is, such as the overview, which knows the
 * item and the path to the list. A list shown without one is not dragged.
 */
export interface ListEntryDrag {
  /** Put the entry at the position on the transfer of a drag starting. */
  onDragStart: (event: React.DragEvent, position: number) => void
  /** Whether a drag over the list carries something it takes. */
  accepts: (event: React.DragEvent) => boolean
  /** Take what was dropped at a position: an entry's, or the one past the
   * last. Returns whether it was taken. */
  onDrop: (event: React.DragEvent, position: number) => boolean
}

export const ListEntryDragContext = React.createContext<ListEntryDrag | null>(null)
