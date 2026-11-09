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
import {
  entryKey,
  repeatedPositions,
} from 'src/components/attribute/value/list_unique'
import {
  newAttribute,
  type Attribute,
  type AttributeValueTypes,
} from 'src/models/attribute'
import { AttributeValueType } from 'src/models/attribute_value_type'
import type { Code } from 'src/models/code'

function code(scheme: string, value: string, meaning: string): Code {
  return { code: value, scheme, meaning, schemeVersion: null }
}

const MELANOMA = code('SCT', '1162635006', 'Malignant melanoma')
const SCAR = code('SCT', '12402003', 'Scar')

function codeEntry(
  value: Code | null,
  mappable: string | null = null,
): Attribute<AttributeValueTypes> {
  return {
    ...newAttribute<AttributeValueTypes>(
      'schema-uid',
      AttributeValueType.CODE,
      value,
      '',
    ),
    mappableValue: mappable,
  }
}

function textEntry(value: string): Attribute<AttributeValueTypes> {
  return newAttribute<AttributeValueTypes>(
    'schema-uid',
    AttributeValueType.STRING,
    value,
    value,
  )
}

describe('repeatedPositions', () => {
  it('marks the later of two entries of the same code', () => {
    // Act
    const repeated = repeatedPositions([
      codeEntry(MELANOMA),
      codeEntry(SCAR),
      codeEntry(MELANOMA),
    ])

    // Assert
    expect([...repeated]).toEqual([2])
  })

  it('tells a code by its scheme and code, not how its meaning reads', () => {
    // Act
    const repeated = repeatedPositions([
      codeEntry(MELANOMA),
      codeEntry({ ...MELANOMA, meaning: 'Melanoma, malignant' }),
    ])

    // Assert
    expect([...repeated]).toEqual([1])
  })

  it('compares text to map by trimmed, and not with a code', () => {
    // Act
    const repeated = repeatedPositions([
      codeEntry(null, 'M80702'),
      codeEntry(MELANOMA),
      codeEntry(null, ' M80702 '),
    ])

    // Assert
    expect([...repeated]).toEqual([2])
  })

  it('does not compare entries saying nothing', () => {
    // Act
    const repeated = repeatedPositions([codeEntry(null), codeEntry(null)])

    // Assert
    expect(repeated.size).toBe(0)
  })

  it('compares text trimmed', () => {
    // Act
    const repeated = repeatedPositions([textEntry('Seen'), textEntry(' Seen ')])

    // Assert
    expect([...repeated]).toEqual([1])
  })
})

describe('entryKey', () => {
  it('says nothing of an entry without a value or text to map by', () => {
    // Act
    const key = entryKey(codeEntry(null, '  '))

    // Assert
    expect(key).toBeNull()
  })
})
