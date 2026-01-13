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

import React, { useMemo } from 'react'

import { Chip } from '@mui/material'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import { ValueDisplayType } from 'src/models/value_display_type'

interface ValueMenuProps {
  attribute: Attribute<AttributeValueTypes>
  valueToDisplay: ValueDisplayType
  setValueToDisplay: (value: ValueDisplayType) => void
}

export default function ValueMenu({
  attribute,
  valueToDisplay,
  setValueToDisplay,
}: ValueMenuProps): React.ReactElement {
  const availableDisplayTypes = useMemo(() => {
    const types: ValueDisplayType[] = []
    if (attribute.updatedValue !== null) {
      types.push(ValueDisplayType.UPDATED)
    }
    if (attribute.mappedValue !== null) {
      types.push(ValueDisplayType.MAPPED)
    }
    if (attribute.originalValue !== null) {
      types.push(ValueDisplayType.ORIGINAL)
    }
    return types
  }, [attribute.updatedValue, attribute.originalValue, attribute.mappedValue])

  const activeValue = useMemo(() => {
    if (attribute.updatedValue !== null) {
      return ValueDisplayType.UPDATED
    }
    if (attribute.mappedValue !== null) {
      return ValueDisplayType.MAPPED
    }
    if (attribute.originalValue !== null) {
      return ValueDisplayType.ORIGINAL
    }
    return ValueDisplayType.CURRENT
  }, [attribute.updatedValue, attribute.mappedValue, attribute.originalValue])
  const handleClick = (): void => {
    const currentIndex = availableDisplayTypes.indexOf(valueToDisplay)
    const nextIndex = (currentIndex + 1) % availableDisplayTypes.length
    setValueToDisplay(availableDisplayTypes[nextIndex])
  }

  const getLabel = (): string => {
    switch (valueToDisplay) {
      case ValueDisplayType.ORIGINAL:
        return 'O'
      case ValueDisplayType.UPDATED:
        return 'U'
      case ValueDisplayType.MAPPED:
        return 'M'
      default:
        return 'C'
    }
  }

  return (
    <Chip
      label={getLabel()}
      disabled={availableDisplayTypes.length <= 1}
      onClick={handleClick}
      variant={valueToDisplay === activeValue ? 'filled' : 'outlined'}
      clickable
      size="small"
    />
  )
}
