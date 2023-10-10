import React, { type ReactElement, Fragment } from 'react'
import { Typography } from '@mui/material'

export default function Title(): ReactElement {
  return (
    <Fragment>
      <Typography variant="h4">Welcome to the SlideTap WebApp</Typography>
    </Fragment>
  )
}
