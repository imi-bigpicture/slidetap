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

import { describe, expect, it } from 'vitest'
import { splitTagSelection } from 'src/components/item/tag_selection'
import { NIL_UID } from 'src/models/attribute'
import type { Tag } from 'src/models/tag'

function tag(uid: string, name: string): Tag {
  return { uid, name, color: null, description: null }
}

describe('splitTagSelection', () => {
  it('keeps the uids of existing tags', () => {
    // Act
    const selection = splitTagSelection([tag('uid-1', 'Reviewed'), tag('uid-2', 'Rescan')])

    // Assert
    expect(selection).toEqual({ tagUids: ['uid-1', 'uid-2'], newTagNames: [] })
  })

  it('takes a name typed in as a new tag', () => {
    // Act
    const selection = splitTagSelection([tag('uid-1', 'Reviewed'), 'Rescan'])

    // Assert
    expect(selection).toEqual({ tagUids: ['uid-1'], newTagNames: ['Rescan'] })
  })

  it('takes a new tag shown back with the nil uid as still to be created', () => {
    // Act
    const selection = splitTagSelection([tag(NIL_UID, 'Rescan')])

    // Assert
    expect(selection).toEqual({ tagUids: [], newTagNames: ['Rescan'] })
  })

  it('selects nothing from an empty selection', () => {
    // Act
    const selection = splitTagSelection([])

    // Assert
    expect(selection).toEqual({ tagUids: [], newTagNames: [] })
  })
})
