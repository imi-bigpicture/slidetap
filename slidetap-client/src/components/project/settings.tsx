import { Button, Stack, TextField } from '@mui/material'
import { Box } from '@mui/system'
import AttributeDetails from 'components/attribute/attribute_details'
import StepHeader from 'components/step_header'
import { Action } from 'models/action'
import type { Project } from 'models/project'
import React, { Fragment, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import projectApi from 'services/api/project_api'

interface SettingsProps {
  project: Project
  setProject: React.Dispatch<React.SetStateAction<Project | undefined>>
}

export default function Settings({ project, setProject }: SettingsProps): ReactElement {
  const navigate = useNavigate()

  function handleCreateProject(event: React.MouseEvent<HTMLElement>): void {
    projectApi
      .create(project?.name)
      .then((project) => {
        navigate('/project/' + project.uid + '/settings')
      })
      .catch((x) => {
        console.error('Failed to get images', x)
      })
  }

  function handleUpdateProject(event: React.MouseEvent<HTMLElement>): void {
    projectApi.update(project).catch((x) => {
      console.error('Failed to update project', x)
    })
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
          <AttributeDetails
            schemas={project.schema.attributes}
            attributes={project.attributes}
            action={Action.VIEW}
            handleAttributeOpen={() => {}}
            handleAttributeUpdate={() => {}}
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
