//    Copyright 2024 SECTRA AB
//
//    Licensed under the Apache License, Version 2.0 (the "License");
//    you may not use this file except in compliance with the License.
//    You may obtain a copy of the License at
//
//        http://www.apache.org/licenses/LICENSE-2.0
//
//    Unless required by applicable law or agreed to in writing, software
//    distributed under the License is distributed on an "AS IS" BASIS,
//    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
//    See the License for the specific language governing permissions and
//    limitations under the License.

import { Button, TextField } from '@mui/material'
import Grid from '@mui/material/Grid2'
import AttributeDetails from 'components/attribute/attribute_details'
import StepHeader from 'components/step_header'
import { Action } from 'models/action'
import type { Attribute } from 'models/attribute'
import type { Project } from 'models/project'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import projectApi from 'services/api/project_api'
import { useSchemaContext } from '../../contexts/schema_context'

interface SettingsProps {
  project: Project
  setProject: (project: Project) => void
}

export default function Settings({ project, setProject }: SettingsProps): ReactElement {
  const navigate = useNavigate()
  const rootSchema = useSchemaContext()
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

  const baseHandleAttributeUpdate = (tag: string, attribute: Attribute<any>): void => {
    const updatedAttributes = { ...project.attributes }
    updatedAttributes[tag] = attribute
    const updatedProject = { ...project, attributes: updatedAttributes }
    setProject(updatedProject)
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid size={{ xs: 12 }}>
        <StepHeader title="Project settings" />
      </Grid>
      <Grid size={{ xs: 2 }}>
        <TextField
          label="Project Name"
          variant="standard"
          onChange={handleNameChange}
          defaultValue={project.name}
          autoFocus
        />
      </Grid>
      <Grid size={{ xs: 6 }}>
        <AttributeDetails
          schemas={rootSchema?.project.attributes ?? {}}
          attributes={project.attributes}
          action={Action.EDIT}
          handleAttributeOpen={() => {}}
          handleAttributeUpdate={baseHandleAttributeUpdate}
        />
      </Grid>
      <Grid size={{ xs: 12 }}>
        {project.uid === '' ? (
          <Button onClick={handleCreateProject}>Create</Button>
        ) : (
          <Button onClick={handleUpdateProject}>Update</Button>
        )}
      </Grid>
    </Grid>
  )
}
