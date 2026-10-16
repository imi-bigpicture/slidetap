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

import { NIL_UID } from 'src/models/attribute'
import type { Tag } from 'src/models/tag'

export interface TagSelection {
  /** The uids of the existing tags selected. */
  tagUids: string[]
  /** The names of the tags selected that are still to be created. */
  newTagNames: string[]
}

/** Splits what is selected in the tag field into existing tags and new ones.
 *
 * A tag not yet saved is typed in as a string, and shown back as a tag with
 * the nil uid. Either way it is a name still to be created, not a reference to
 * an existing tag.
 */
export function splitTagSelection(selection: (string | Tag)[]): TagSelection {
  const tagUids: string[] = []
  const newTagNames: string[] = []
  for (const selected of selection) {
    if (typeof selected === 'string') {
      newTagNames.push(selected)
    } else if (selected.uid === NIL_UID) {
      newTagNames.push(selected.name)
    } else {
      tagUids.push(selected.uid)
    }
  }
  return { tagUids, newTagNames }
}
