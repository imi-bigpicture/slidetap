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

import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import { selectValueToDisplay } from './value_to_display'
import { ValueDisplayType } from 'src/models/value_display_type'

/** What an entry of a list says, to tell two that say the same, by the rules
 * the server validates a list of unique entries by.
 *
 * Its effective value: a code by its scheme and code, not by how its meaning
 * reads, text trimmed, and a measurement by its value and unit. One still to
 * be mapped by the text it is to be mapped by, trimmed, which is not compared
 * with one that is mapped. Null for one that says nothing, and for one holding
 * others, which are not compared.
 */
export function entryKey(entry: Attribute<AttributeValueTypes>): string | null {
  const value = selectValueToDisplay(entry, ValueDisplayType.CURRENT)
  if (value === null || value === undefined) {
    const mappable = entry.mappableValue?.trim() ?? ''
    return mappable !== '' ? `mappable\u0000${mappable}` : null
  }
  if (typeof value === 'string') {
    const text = value.trim()
    return text !== '' ? `text\u0000${text}` : null
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return `${typeof value}\u0000${String(value)}`
  }
  if (value instanceof Date) {
    return `date\u0000${value.toISOString()}`
  }
  if (typeof value === 'object' && 'code' in value && 'scheme' in value) {
    return `code\u0000${value.scheme}\u0000${value.code}`
  }
  if (typeof value === 'object' && 'value' in value && 'unit' in value) {
    return `measurement\u0000${String(value.value)}\u0000${String(value.unit)}`
  }
  return null
}

/** The positions of the entries that say what an entry before them says. The
 * first of each stays unmarked, as it is the later ones that are to go. */
export function repeatedPositions(
  entries: ReadonlyArray<Attribute<AttributeValueTypes>>,
): Set<number> {
  const seen = new Set<string>()
  const repeated = new Set<number>()
  entries.forEach((entry, position) => {
    const key = entryKey(entry)
    if (key === null) return
    if (seen.has(key)) {
      repeated.add(position)
    } else {
      seen.add(key)
    }
  })
  return repeated
}
