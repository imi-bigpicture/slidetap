import { Stack, Typography } from '@mui/material'
import React from 'react'

interface StepHeaderProps {
  title: string
  description?: string
  instructions?: string
}

export default function StepHeader({
  title,
  description,
  instructions,
}: StepHeaderProps): React.ReactElement {
  return (
    <Stack alignItems="flex-start" justifyContent="flex-start">
      <Typography variant="h4">{title}</Typography>
      {description !== undefined && <Typography variant="h6">{description}</Typography>}
      {instructions !== undefined && (
        <Typography variant="subtitle1">{instructions}</Typography>
      )}
    </Stack>
  )
}
