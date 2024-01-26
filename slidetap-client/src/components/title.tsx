import { Box, Typography } from '@mui/material'
import React from 'react'

export default function Title(): React.ReactElement {
  return (
    <Box margin={2}>
      <Typography variant="h4">Welcome to the SlideTap WebApp</Typography>
    </Box>
  )
}
