import React, { ReactElement } from 'react'
import { TextField } from '@mui/material'
import { Project } from 'models/project'

interface BatchesProps {
  project: Project
}

export default function Batches({ project }: BatchesProps): ReactElement {
  return <TextField label="Batch" variant="standard" defaultValue={project} />
}
