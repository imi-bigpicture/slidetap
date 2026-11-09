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
import {
  Box,
  ButtonBase,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
  alpha,
} from '@mui/material'
import React, { type ReactElement } from 'react'
import {
  GroupStatus,
  STATUS_DISPLAY,
  STATUS_SEVERITY,
  groupStatus,
  statusRanges,
} from 'src/components/project/group_status'
import GroupValue from 'src/components/project/group_value'
import type {
  ItemGroupSummary,
  ItemGroupValuePart,
  ItemGrouping,
} from 'src/models/item_grouping'

/** Values as a reader orders them: "53-62 years" after "18-52 years". */
const compareValues = (first: string, second: string): number =>
  first.localeCompare(second, undefined, { numeric: true, sensitivity: 'base' })

interface GroupGridProps {
  grouping: ItemGrouping
  onOpenGroup: (group: ItemGroupSummary) => void
}

/**
 * The groups laid out as a grid: one column of the grouping down the side, one
 * across the top, and a line in each cell for every group the other columns
 * tell apart there. Each group is coloured by how it stands against the
 * minimum, so a row or a column of groups that are too small, or close to it,
 * shows at a glance.
 *
 * Which columns go where is picked here, starting with the first down the side
 * and the last across: for skin, the diagnoses by the age bucket, with the site
 * and the sex on the lines of a cell.
 */
export default function GroupGrid({
  grouping,
  onOpenGroup,
}: GroupGridProps): ReactElement {
  const { columns, policy } = grouping
  const [rowColumn, setRowColumn] = React.useState(0)
  const [acrossColumn, setAcrossColumn] = React.useState(
    Math.max(columns.length - 1, 0),
  )
  const lineColumns = columns
    .map((_, index) => index)
    .filter((index) => index !== rowColumn && index !== acrossColumn)

  const rowValues = [
    ...new Set(grouping.groups.map((group) => group.values[rowColumn] ?? '')),
  ].sort(compareValues)
  const acrossValues = [
    ...new Set(grouping.groups.map((group) => group.values[acrossColumn] ?? '')),
  ].sort(compareValues)
  const cells = new Map<string, ItemGroupSummary[]>()
  for (const group of grouping.groups) {
    const key = `${group.values[rowColumn]}\u0000${group.values[acrossColumn]}`
    cells.set(key, [...(cells.get(key) ?? []), group])
  }
  /** What the value of a column is made of, by its text: the same in every
   * group that has it. */
  const partsOf = (column: number): Map<string, ItemGroupValuePart[]> =>
    new Map(
      grouping.groups.map((group) => [
        group.values[column] ?? '',
        group.parts[column] ?? [],
      ]),
    )
  const rowParts = partsOf(rowColumn)
  const acrossParts = partsOf(acrossColumn)
  /** A value as its parts read, e.g. the meaning of a code without the code,
   * which the tooltip of the cell still gives. Its text where it has no parts. */
  const shortValue = (group: ItemGroupSummary, column: number): string => {
    const parts = group.parts[column] ?? []
    return parts.length > 0
      ? parts.map((part) => part.label).join(' + ')
      : (group.values[column] ?? '')
  }
  const lineLabel = (group: ItemGroupSummary): string =>
    lineColumns.map((index) => shortValue(group, index)).join(', ')
  const countName = policy.countDisplayName.toLowerCase()

  const columnPicker = (
    label: string,
    value: number,
    onChange: (index: number) => void,
  ): ReactElement => (
    <FormControl size="small" sx={{ minWidth: 180 }}>
      <InputLabel>{label}</InputLabel>
      <Select
        label={label}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      >
        {columns.map((name, index) => (
          <MenuItem key={name} value={index}>
            {name}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )

  return (
    <Stack spacing={1}>
      <Stack
        direction="row"
        spacing={2}
        useFlexGap
        sx={{ alignItems: 'center', flexWrap: 'wrap' }}
      >
        {columnPicker('Rows', rowColumn, (index) => {
          if (index === acrossColumn) setAcrossColumn(rowColumn)
          setRowColumn(index)
        })}
        {columnPicker('Columns', acrossColumn, (index) => {
          if (index === rowColumn) setRowColumn(acrossColumn)
          setAcrossColumn(index)
        })}
        {/* The legend: what each colour says, with its icon and its range. */}
        {statusRanges(policy).map(({ status, range }) => {
          const display = STATUS_DISPLAY[status]
          return (
            <Chip
              key={status}
              size="small"
              variant="outlined"
              color={display.color}
              icon={display.icon}
              label={`${status}: ${range} ${countName}`}
            />
          )
        })}
      </Stack>
      <TableContainer sx={{ maxHeight: 'calc(100vh - 260px)' }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>
                {columns[rowColumn]} / {columns[acrossColumn]}
              </TableCell>
              {acrossValues.map((value) => (
                <TableCell key={value} align="center">
                  <GroupValue
                    text={value}
                    parts={acrossParts.get(value)}
                    justify="center"
                  />
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rowValues.map((rowValue) => (
              <TableRow key={rowValue}>
                <TableCell component="th" scope="row" sx={{ maxWidth: 360 }}>
                  <GroupValue text={rowValue} parts={rowParts.get(rowValue)} />
                </TableCell>
                {acrossValues.map((acrossValue) => {
                  const groups = [
                    ...(cells.get(`${rowValue}\u0000${acrossValue}`) ?? []),
                  ].sort(
                    (first, second) =>
                      STATUS_SEVERITY[groupStatus(first, policy)] -
                        STATUS_SEVERITY[groupStatus(second, policy)] ||
                      compareValues(lineLabel(first), lineLabel(second)),
                  )
                  return (
                    <TableCell key={acrossValue} align="center" sx={{ p: 0.5 }}>
                      {groups.length === 0 ? (
                        <Typography variant="body2" color="text.disabled">
                          –
                        </Typography>
                      ) : (
                        <Stack spacing={0.5}>
                          {groups.map((group) => (
                            <GroupCell
                              key={group.values.join('\u0000')}
                              group={group}
                              status={groupStatus(group, policy)}
                              line={lineColumns.length > 0 ? lineLabel(group) : null}
                              countName={countName}
                              columns={columns}
                              onOpen={() => onOpenGroup(group)}
                            />
                          ))}
                        </Stack>
                      )}
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  )
}

interface GroupCellProps {
  group: ItemGroupSummary
  status: GroupStatus
  /** What tells this group from the others in its cell, if anything does. */
  line: string | null
  countName: string
  columns: string[]
  onOpen: () => void
}

/** One group in a cell: its count, tinted and marked by its status, opening
 * the group when clicked. */
function GroupCell({
  group,
  status,
  line,
  countName,
  columns,
  onOpen,
}: GroupCellProps): ReactElement {
  const display = STATUS_DISPLAY[status]
  return (
    <Tooltip
      title={
        <Box>
          {columns.map((name, index) => (
            <Typography key={name} variant="caption" sx={{ display: 'block' }}>
              {name}: {group.values[index]}
            </Typography>
          ))}
          <Typography variant="caption" sx={{ display: 'block' }}>
            {group.count} {countName}, {group.items.length} items · {status}
          </Typography>
        </Box>
      }
    >
      <ButtonBase
        onClick={onOpen}
        sx={(theme) => ({
          width: '100%',
          minWidth: 64,
          px: 1,
          py: 0.5,
          gap: 0.5,
          borderRadius: 1,
          justifyContent: 'center',
          color: 'text.primary',
          backgroundColor: alpha(theme.palette[display.color].main, 0.22),
          border: `1px solid ${alpha(theme.palette[display.color].main, 0.6)}`,
          '&:hover': {
            backgroundColor: alpha(theme.palette[display.color].main, 0.36),
          },
        })}
      >
        <Box
          component="span"
          sx={{ color: `${display.color}.main`, display: 'flex', fontSize: 16 }}
        >
          {display.icon}
        </Box>
        <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
          {group.count}
        </Typography>
        {line !== null && (
          <Typography variant="caption" component="span" color="text.secondary" noWrap>
            {line}
          </Typography>
        )}
      </ButtonBase>
    </Tooltip>
  )
}
