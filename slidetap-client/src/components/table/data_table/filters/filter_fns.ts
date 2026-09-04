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

import type { FilterSpec } from '../types'

/**
 * How each filter variant decides whether a row is kept.
 *
 * Written here rather than taken from TanStack's built-ins, which choose a
 * function from the type of the value in the cell and so cannot know what shape
 * the filter above it produces. A status column holding a numeric enum filtered
 * by a list of picked values would be read as a numeric range, keeping
 * everything between the lowest and highest pick.
 */
export type RowFilter = (value: unknown, filterValue: unknown) => boolean

/** Case-insensitive substring, over whatever the cell holds written out. */
const textFilter: RowFilter = (value, filterValue) => {
  if (typeof filterValue !== 'string' || filterValue === '') return true
  return asText(value).toLowerCase().includes(filterValue.toLowerCase())
}

/** Exactly the picked value, compared as written so 'true' matches `true`. */
const selectFilter: RowFilter = (value, filterValue) => {
  if (typeof filterValue !== 'string' || filterValue === '') return true
  return asText(value) === filterValue
}

/**
 * Any of the picked values.
 *
 * A cell holding a list is kept when it carries any of them; one holding a
 * single value is kept when it is one of them. Nothing picked filters nothing.
 */
const multiSelectFilter: RowFilter = (value, filterValue) => {
  if (!Array.isArray(filterValue) || filterValue.length === 0) return true
  const picked = filterValue.map((entry) => asText(entry))
  if (Array.isArray(value)) {
    return value.some((entry) => picked.includes(asText(entry)))
  }
  return picked.includes(asText(value))
}

/** Between two numbers, either of which may be left open. */
const rangeFilter: RowFilter = (value, filterValue) => {
  if (!Array.isArray(filterValue)) return true
  const [low, high] = filterValue as Array<number | null>
  if (low == null && high == null) return true
  const amount = Number(value)
  if (Number.isNaN(amount)) return false
  if (low != null && amount < low) return false
  if (high != null && amount > high) return false
  return true
}

/**
 * Between two dates, either of which may be left open.
 *
 * The bounds are whole days: picking the same date at both ends asks for that
 * day, not for the instant midnight fell on it.
 */
const dateRangeFilter: RowFilter = (value, filterValue) => {
  if (!Array.isArray(filterValue)) return true
  const [from, to] = filterValue as Array<Date | null>
  if (from == null && to == null) return true
  const at = toDate(value)
  if (at === null) return false
  if (from != null && at < startOfDay(from)) return false
  if (to != null && at > endOfDay(to)) return false
  return true
}

const FILTERS: Record<FilterSpec['variant'], RowFilter> = {
  text: textFilter,
  select: selectFilter,
  'multi-select': multiSelectFilter,
  range: rangeFilter,
  'date-range': dateRangeFilter,
}

export function filterFor(spec: FilterSpec): RowFilter {
  return FILTERS[spec.variant]
}

function asText(value: unknown): string {
  if (value === null || value === undefined) return ''
  if (value instanceof Date) return value.toISOString()
  return String(value)
}

/** A cell's value as a date, whether it arrived as one or as an ISO string. */
function toDate(value: unknown): Date | null {
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value
  if (typeof value === 'string' || typeof value === 'number') {
    const at = new Date(value)
    return Number.isNaN(at.getTime()) ? null : at
  }
  return null
}

function startOfDay(date: Date): Date {
  const start = new Date(date)
  start.setHours(0, 0, 0, 0)
  return start
}

function endOfDay(date: Date): Date {
  const end = new Date(date)
  end.setHours(23, 59, 59, 999)
  return end
}
