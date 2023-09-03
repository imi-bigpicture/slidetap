import React, { ReactElement, Fragment } from 'react'
import { Button, Stack, TextField } from '@mui/material'
import { Box } from '@mui/system'
import { Project } from 'models/project'
import projectApi from 'services/api/project_api'
import { useNavigate } from 'react-router-dom'
import StepHeader from 'components/step_header'

interface SettingsProps {
  project: Project
  setProject: React.Dispatch<React.SetStateAction<Project>>
}

export default function Settings({ project, setProject }: SettingsProps): ReactElement {
  const navigate = useNavigate()

  function handleCreateProject(event: React.MouseEvent<HTMLElement>): void {
    projectApi
      .create(project?.name)
      .then((project) => {
        navigate('/project/' + project.uid + '/settings')
      })
      .catch((x) => console.error('Failed to get images', x))
  }

  function handleUpdateProject(event: React.MouseEvent<HTMLElement>): void {
    projectApi
      .update(project)
      .catch((x) => console.error('Failed to update project', x))
    setProject(project)
  }

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const { value } = event.target
    project.name = value
    setProject(project)
  }

  return (
    <Fragment>
      <StepHeader title="Project settings" />
      <br />
      <Box sx={{ width: 300 }}>
        <Stack spacing={2}>
          <TextField
            label="Project Name"
            variant="standard"
            onChange={handleNameChange}
            defaultValue={project.name}
            autoFocus
          />
          {project.uid === '' ? (
            <Button onClick={handleCreateProject}>Create</Button>
          ) : (
            <Button onClick={handleUpdateProject}>Update</Button>
          )}
        </Stack>
      </Box>
    </Fragment>
  )
}
