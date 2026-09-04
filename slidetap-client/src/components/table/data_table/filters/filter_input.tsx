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

import { useEffect, useRef, useState, type ReactElement } from 'react'
import {
  Box,
  Checkbox,
  FormControl,
  Chip,
  ListItemText,
  MenuItem,
  Select,
  TextField,
  Tooltip,
} from '@mui/material'
import { DatePicker } from '@mui/x-date-pickers'
import type { FilterOption, FilterSpec } from '../types'

/** How long typing settles before the table is asked to filter. */
const TYPING_SETTLES_MS = 400

/**
 * Holds what is being entered, handing it on once entering has settled.
 *
 * Every box that is typed into needs this, not just the text one: a filter the
 * table acts on per keystroke is a request per keystroke, and against a server
 * "12" in a range box asks once for everything from 1 and again for everything
 * from 12.
 */
function useSettledValue<T>(
  committed: T,
  onChange: (value: T) => void,
): [T, (next: T) => void] {
  const committedKey = JSON.stringify(committed ?? null)
  const [entered, setEntered] = useState<T>(committed)
  const [enteredKey, setEnteredKey] = useState(committedKey)

  // Follows the value when it is changed from outside — a filter cleared from
  // the toolbar — without fighting what is being entered.
  useEffect(() => {
    setEntered(committed)
    setEnteredKey(committedKey)
    // The value itself is a fresh array on every render for the range boxes, so
    // it is compared by what it says rather than by identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [committedKey])

  // The caller's `onChange` is a fresh arrow on every render of the table, so
  // it is held in a ref rather than depended on: in the dependency list it
  // would restart the timer on each render, and a table that re-renders faster
  // than this settles would never commit what was entered.
  const latestOnChange = useRef(onChange)
  useEffect(() => {
    latestOnChange.current = onChange
  })

  useEffect(() => {
    if (enteredKey === committedKey) return
    const timer = setTimeout(() => latestOnChange.current(entered), TYPING_SETTLES_MS)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enteredKey, committedKey])

  const set = (next: T): void => {
    setEntered(next)
    setEnteredKey(JSON.stringify(next ?? null))
  }
  return [entered, set]
}

interface FilterInputProps {
  spec: FilterSpec
  /** Put on the control itself, so the column menu can focus it. */
  inputId: string
  value: unknown
  onChange: (value: unknown) => void
  label: string
}

/**
 * The control under a column heading, chosen by what the column says it filters
 * by. Each variant carries its own value shape, and only this file knows what
 * that shape is: everything above passes the value through untouched.
 */
export function FilterInput({
  spec,
  inputId,
  value,
  onChange,
  label,
}: FilterInputProps): ReactElement {
  switch (spec.variant) {
    case 'text':
      return (
        <TextFilter
          inputId={inputId}
          value={value}
          onChange={onChange}
          label={label}
          hint={spec.hint}
        />
      )
    case 'select':
      return (
        <SelectFilter
          inputId={inputId}
          value={value}
          onChange={onChange}
          label={label}
          options={spec.options}
        />
      )
    case 'multi-select':
      return (
        <MultiSelectFilter
          inputId={inputId}
          value={value}
          onChange={onChange}
          label={label}
          options={spec.options}
        />
      )
    case 'range':
      return <RangeFilter inputId={inputId} value={value} onChange={onChange} />
    case 'date-range':
      return <DateRangeFilter inputId={inputId} value={value} onChange={onChange} />
  }
}

/** Free text. Held locally while typing so each keystroke is not a request. */
function TextFilter({
  inputId,
  value,
  onChange,
  label,
  hint,
}: {
  inputId: string
  value: unknown
  onChange: (value: unknown) => void
  label: string
  hint?: string
}): ReactElement {
  const committed = typeof value === 'string' ? value : ''
  const [typed, setTyped] = useSettledValue(committed, (settled) =>
    onChange(settled === '' ? undefined : settled),
  )

  const field = (
    <TextField
      variant="standard"
      placeholder={`Filter ${label}`}
      value={typed}
      onChange={(event) => setTyped(event.target.value)}
      fullWidth
      slotProps={{ htmlInput: { id: inputId, 'aria-label': `Filter ${label}` } }}
    />
  )
  return hint !== undefined ? <Tooltip title={hint}>{field}</Tooltip> : field
}

/** One of a fixed set, or none. */
function SelectFilter({
  inputId,
  value,
  onChange,
  label,
  options,
}: {
  inputId: string
  value: unknown
  onChange: (value: unknown) => void
  label: string
  options: FilterOption[]
}): ReactElement {
  return (
    <FormControl variant="standard" size="small" fullWidth>
      <Select
        value={typeof value === 'string' ? value : ''}
        onChange={(event) =>
          onChange(event.target.value === '' ? undefined : event.target.value)
        }
        displayEmpty
        // The id goes on the element that takes focus. Through  it
        // would land on Select's hidden native input, which is
        // aria-hidden and not tabbable.
        SelectDisplayProps={{ id: inputId, 'aria-label': `Filter ${label}` }}
      >
        <MenuItem value="">
          <Box component="span" sx={{ opacity: 0.6 }}>
            All
          </Box>
        </MenuItem>
        {options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            {option.label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}

/** Any of a fixed set. An empty choice filters nothing rather than everything. */
function MultiSelectFilter({
  inputId,
  value,
  onChange,
  label,
  options,
}: {
  inputId: string
  value: unknown
  onChange: (value: unknown) => void
  label: string
  options: FilterOption[]
}): ReactElement {
  const chosen = Array.isArray(value) ? (value as string[]) : []
  const labelFor = (candidate: string): string =>
    options.find((option) => option.value === candidate)?.label ?? candidate

  return (
    <FormControl variant="standard" size="small" fullWidth>
      <Select
        multiple
        value={chosen}
        onChange={(event) => {
          const next = event.target.value
          const values = typeof next === 'string' ? next.split(',') : next
          onChange(values.length === 0 ? undefined : values)
        }}
        displayEmpty
        // The id goes on the element that takes focus. Through  it
        // would land on Select's hidden native input, which is
        // aria-hidden and not tabbable.
        SelectDisplayProps={{ id: inputId, 'aria-label': `Filter ${label}` }}
        renderValue={(selected) =>
          selected.length === 0 ? (
            <Box component="span" sx={{ opacity: 0.6 }}>
              All
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {selected.map((entry) => (
                <Chip key={entry} label={labelFor(entry)} size="small" />
              ))}
            </Box>
          )
        }
      >
        {options.map((option) => (
          <MenuItem key={option.value} value={option.value}>
            <Checkbox checked={chosen.includes(option.value)} size="small" />
            <ListItemText primary={option.label} />
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )
}

/** Two numbers, either of which may be left open. */
function RangeFilter({
  inputId,
  value,
  onChange,
}: {
  inputId: string
  value: unknown
  onChange: (value: unknown) => void
}): ReactElement {
  const committed: Array<number | null> = Array.isArray(value)
    ? (value as Array<number | null>)
    : [null, null]
  const [bounds, setBounds] = useSettledValue(committed, (settled) =>
    onChange(settled[0] === null && settled[1] === null ? undefined : settled),
  )

  const setBound = (index: 0 | 1, raw: string): void => {
    const next: Array<number | null> = [bounds[0] ?? null, bounds[1] ?? null]
    next[index] = raw === '' ? null : Number(raw)
    setBounds(next)
  }

  return (
    <Box sx={{ display: 'flex', gap: 0.5 }}>
      <TextField
        variant="standard"
        type="number"
        placeholder="Min"
        value={bounds[0] ?? ''}
        onChange={(event) => setBound(0, event.target.value)}
        slotProps={{ htmlInput: { id: inputId, 'aria-label': 'Minimum' } }}
      />
      <TextField
        variant="standard"
        type="number"
        placeholder="Max"
        value={bounds[1] ?? ''}
        onChange={(event) => setBound(1, event.target.value)}
        slotProps={{ htmlInput: { 'aria-label': 'Maximum' } }}
      />
    </Box>
  )
}

/** Two dates, either of which may be left open. */
function DateRangeFilter({
  inputId,
  value,
  onChange,
}: {
  inputId: string
  value: unknown
  onChange: (value: unknown) => void
}): ReactElement {
  const committed: Array<Date | null> = Array.isArray(value)
    ? (value as Array<Date | null>)
    : [null, null]
  // Settled like the other boxes: a date typed rather than picked arrives a
  // character at a time, and each half-written year is a filter of its own.
  const [bounds, setBounds] = useSettledValue(committed, (settled) =>
    onChange(settled[0] === null && settled[1] === null ? undefined : settled),
  )

  const setBound = (index: 0 | 1, date: Date | null): void => {
    const next: Array<Date | null> = [bounds[0] ?? null, bounds[1] ?? null]
    // A date being typed rather than picked arrives as an Invalid Date until
    // it is whole. Held as empty, because that is what a half-written date
    // means, and because an Invalid Date reads the same as empty once written
    // down: committed, it could never be told apart from the empty box the
    // reader clears it back to, and the filter would stick.
    next[index] = date !== null && Number.isNaN(date.getTime()) ? null : date
    setBounds(next)
  }

  return (
    <Box sx={{ display: 'flex', gap: 0.5 }}>
      <DatePicker
        label="From"
        value={bounds[0] ?? null}
        onChange={(date) => setBound(0, date)}
        slotProps={{ textField: { variant: 'standard', id: inputId } }}
      />
      <DatePicker
        label="To"
        value={bounds[1] ?? null}
        onChange={(date) => setBound(1, date)}
        slotProps={{ textField: { variant: 'standard' } }}
      />
    </Box>
  )
}
