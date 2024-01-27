import { Button, TextField } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import AttributeDetails from 'components/attribute/attribute_details'
import StepHeader from 'components/step_header'
import { Action } from 'models/action'
import type { Attribute } from 'models/attribute'
import type { Project } from 'models/project'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import projectApi from 'services/api/project_api'

interface SettingsProps {
  project: Project
  setProject: React.Dispatch<React.SetStateAction<Project | undefined>>
}

export default function Settings({ project, setProject }: SettingsProps): ReactElement {
  const navigate = useNavigate()

  const handleCreateProject = (event: React.MouseEvent<HTMLElement>): void => {
    projectApi
      .create(project?.name)
      .then((project) => {
        navigate('/project/' + project.uid + '/settings')
      })
      .catch((x) => {
        console.error('Failed to get images', x)
      })
  }

  const handleUpdateProject = (event: React.MouseEvent<HTMLElement>): void => {
    projectApi
      .update(project)
      .then((updatedProject) => {
        setProject(updatedProject)
      })
      .catch((x) => {
        console.error('Failed to update project', x)
      })
  }

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const { value } = event.target
    project.name = value
    setProject(project)
  }

  const baseHandleAttributeUpdate = (attribute: Attribute<any, any>): void => {
    const updatedAttributes = { ...project.attributes }
    updatedAttributes[attribute.schema.tag] = attribute
    const updatedProject = { ...project, attributes: updatedAttributes }
    setProject(updatedProject)
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid xs={12}>
        <StepHeader title="Project settings" />
      </Grid>
      <Grid xs={2}>
        <TextField
          label="Project Name"
          variant="standard"
          onChange={handleNameChange}
          defaultValue={project.name}
          autoFocus
        />
      </Grid>
      <Grid xs={6}>
        <AttributeDetails
          schemas={project.schema.attributes}
          attributes={project.attributes}
          action={Action.EDIT}
          handleAttributeOpen={() => {}}
          handleAttributeUpdate={baseHandleAttributeUpdate}
        />
      </Grid>
      <Grid xs={12}>
        {project.uid === '' ? (
          <Button onClick={handleCreateProject}>Create</Button>
        ) : (
          <Button onClick={handleUpdateProject}>Update</Button>
        )}
      </Grid>
    </Grid>
  )
}
