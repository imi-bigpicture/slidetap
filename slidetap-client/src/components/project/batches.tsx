import React, { type ReactElement } from 'react'
import { TextField } from '@mui/material'
import type { Project } from 'models/project'

interface BatchesProps {
  project: Project
}

export default function Batches({ project }: BatchesProps): ReactElement {
  return <TextField label="Batch" variant="standard" defaultValue={project} />
}
