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
import { withHeldAttributeUpdated } from 'src/components/attribute/value/object_update'
import {
  newAttribute,
  RejectedValues,
  type Attribute,
  type AttributeValueTypes,
  type ObjectAttribute,
} from 'src/models/attribute'
import { AttributeValueType } from 'src/models/attribute_value_type'

function text(value: string | null, display: string): Attribute<AttributeValueTypes> {
  return newAttribute<string>('text-schema', AttributeValueType.STRING, value, display)
}

/** A statement holding a Clark level and a pT classification, as imported
 * (the texts of the report) and as mapped. */
function statement(): ObjectAttribute {
  return {
    ...newAttribute<Record<string, Attribute<AttributeValueTypes>>>(
      'statement-schema',
      AttributeValueType.OBJECT,
      null,
      '',
    ),
    originalValue: {
      clark_level: text(null, 'III-IV.'),
      pt: text(null, 'pT1a i detta material.'),
    },
    mappedValue: {
      clark_level: text('III-IV', 'III-IV'),
      pt: text('pT1a', 'pT1a'),
    },
  } as ObjectAttribute
}

describe('withHeldAttributeUpdated', () => {
  it('keeps what was mapped of the attributes not edited', () => {
    // Arrange
    const attribute = statement()

    // Act
    const updated = withHeldAttributeUpdated(attribute, 'pt', text('pT1b', 'pT1b'))

    // Assert
    expect(updated.updatedValue?.clark_level).toBe(attribute.mappedValue?.clark_level)
    expect(updated.updatedValue?.pt.updatedValue).toBe('pT1b')
  })

  it('starts from what was imported where nothing was mapped', () => {
    // Arrange
    const attribute = { ...statement(), mappedValue: null }

    // Act
    const updated = withHeldAttributeUpdated(attribute, 'pt', text('pT1b', 'pT1b'))

    // Assert
    expect(updated.updatedValue?.clark_level).toBe(attribute.originalValue?.clark_level)
  })

  it('starts from what was imported where the mapping was refused', () => {
    // Arrange
    const attribute = { ...statement(), rejected: RejectedValues.MAPPABLE }

    // Act
    const updated = withHeldAttributeUpdated(attribute, 'pt', text('pT1b', 'pT1b'))

    // Assert
    expect(updated.updatedValue?.clark_level).toBe(attribute.originalValue?.clark_level)
  })

  it('edits on top of what was edited before', () => {
    // Arrange
    const attribute = withHeldAttributeUpdated(
      statement(),
      'clark_level',
      text('IV', 'IV'),
    )

    // Act
    const updated = withHeldAttributeUpdated(attribute, 'pt', text('pT1b', 'pT1b'))

    // Assert
    expect(updated.updatedValue?.clark_level.updatedValue).toBe('IV')
    expect(updated.updatedValue?.pt.updatedValue).toBe('pT1b')
  })

  it('leaves the attribute it is given as it was', () => {
    // Arrange
    const attribute = withHeldAttributeUpdated(
      statement(),
      'clark_level',
      text('IV', 'IV'),
    )
    const before = attribute.updatedValue
    const ptBefore = attribute.updatedValue?.pt

    // Act
    withHeldAttributeUpdated(attribute, 'pt', text('pT1b', 'pT1b'))

    // Assert
    expect(attribute.updatedValue).toBe(before)
    expect(attribute.updatedValue?.pt).toBe(ptBefore)
    expect(attribute.updatedValue?.pt.updatedValue).toBe('pT1a')
  })
})
