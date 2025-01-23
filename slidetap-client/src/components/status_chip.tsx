import { Chip } from '@mui/material'
import { ReactElement } from 'react'

interface StatusChipProps<T extends string | number | symbol> {
  status: T
  colorMap: Record<T, 'success' | 'error' | 'primary' | 'secondary'>
  stringMap: Record<T, string>
  onClick?: () => void
}

function StatusChip<T extends string | number | symbol>({
  status,
  colorMap,
  stringMap,
  onClick,
}: StatusChipProps<T>): ReactElement {
  return (
    <Chip
      label={stringMap[status]}
      color={colorMap[status]}
      variant="outlined"
      onClick={onClick}
    />
  )
}
export default StatusChip
