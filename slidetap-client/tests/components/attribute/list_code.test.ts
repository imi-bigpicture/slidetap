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
import { withCodeDisplayValue } from 'src/components/attribute/value/list_code'
import { newAttribute, type CodeAttribute } from 'src/models/attribute'
import { AttributeValueType } from 'src/models/attribute_value_type'
import type { Code } from 'src/models/code'

function emptyCode(): CodeAttribute {
  return newAttribute<Code>(
    'schema-uid',
    AttributeValueType.CODE,
    null,
    'what it said before',
  ) as CodeAttribute
}

describe('withCodeDisplayValue', () => {
  it('reads as the meaning of a picked code', () => {
    // Arrange
    const child: CodeAttribute = {
      ...emptyCode(),
      updatedValue: {
        code: '254701007',
        scheme: 'SCT',
        meaning: 'Basal cell carcinoma',
        schemeVersion: null,
      },
    }

    // Act
    const shown = withCodeDisplayValue(child)

    // Assert
    expect(shown.displayValue).toBe('Basal cell carcinoma')
  })

  it('reads as the text typed to map a code by', () => {
    // Arrange
    const child: CodeAttribute = { ...emptyCode(), mappableValue: 'M80702' }

    // Act
    const shown = withCodeDisplayValue(child)

    // Assert
    expect(shown.displayValue).toBe('M80702')
  })

  it('reads as nothing once emptied', () => {
    // Arrange
    const child = emptyCode()

    // Act
    const shown = withCodeDisplayValue(child)

    // Assert
    expect(shown.displayValue).toBe('')
  })
})
