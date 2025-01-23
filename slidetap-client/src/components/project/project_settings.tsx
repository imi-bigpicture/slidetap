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
import { useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import AttributeDetails from 'src/components/attribute/attribute_details'
import { Action } from 'src/models/action'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { Project } from 'src/models/project'
import projectApi from 'src/services/api/project_api'
import { useSchemaContext } from '../../contexts/schema/schema_context'

interface ProjectSettingsProps {
  project: Project
}

export default function ProjectSettings({
  project,
}: ProjectSettingsProps): ReactElement {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const rootSchema = useSchemaContext()
  const handleCreateProject = (): void => {
    projectApi
      .create(project?.name)
      .then((project) => {
        navigate('/project/' + project.uid + '/settings')
      })
      .catch((x) => {
        console.error('Failed to get images', x)
      })
  }

  const handleUpdateProject = (): void => {
    projectApi
      .update(project)
      .then((updatedProject) => {
        queryClient.setQueryData(['project', project.uid], updatedProject)
      })
      .catch((x) => {
        console.error('Failed to update project', x)
      })
  }

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const { value } = event.target
    queryClient.setQueryData(['project', project.uid], {
      ...project,
      name: value,
    })
  }

  const baseHandleAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    const updatedAttributes = { ...project.attributes }
    updatedAttributes[tag] = attribute
    const updatedProject = { ...project, attributes: updatedAttributes }
    queryClient.setQueryData(['project', project.uid], updatedProject)
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      {/* <Grid size={{ xs: 12 }}>
        <StepHeader title="Project settings" />
      </Grid> */}
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
