import React, { ReactNode, ReactElement, CSSProperties } from 'react'
import CircularProgress from '@mui/material/CircularProgress'
import { Box } from '@mui/material'

interface SpinnerProps {
  loading: boolean
  children: ReactNode
  style?: CSSProperties
  minHeight?: string
}

export default function Spinner({
  loading,
  children,
  style,
  minHeight,
}: SpinnerProps): ReactElement {
  if (style === undefined) {
    style = { display: 'flex', justifyContent: 'center' }
  }
  if (minHeight === undefined) {
    minHeight = '50vh'
  }
  if (loading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight={minHeight}
      >
        <CircularProgress />
      </Box>
    )
  }
  return <>{children}</>
}
