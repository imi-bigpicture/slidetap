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

import { Button, Chip, Divider, TextField } from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import AttributeDetails from 'src/components/attribute/attribute_details'
import { useError } from 'src/contexts/error/error_context'
import { ItemDetailAction } from 'src/models/action'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { Project } from 'src/models/project'
import mapperApi from 'src/services/api/mapper_api'
import projectApi from 'src/services/api/project_api'
import { queryKeys } from 'src/services/query_keys'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import Spinner from '../spinner'
import MapperGroupSelect from './mapper_group_select'

interface ProjectSettingsProps {
  project: Project
  setProject: (project: Project) => void
}

export default function ProjectSettings({
  project,
  setProject,
}: ProjectSettingsProps): ReactElement {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const { showError } = useError()
  const rootSchema = useSchemaContext()
  const mapperGroupsQuery = useQuery({
    queryKey: queryKeys.mapperGroup.all,
    queryFn: async () => {
      return await mapperApi.getMapperGroups()
    },
  })
  const handleCreateProject = (): void => {
    projectApi
      .create(project?.name)
      .then((project) => {
        navigate('/project/' + project.uid + '/settings')
      })
      .catch((error) => {
        showError('Failed to create project', error)
      })
  }

  const projectUpdateMutation = useMutation({
    mutationFn: (project: Project) => {
      return projectApi.update(project)
    },
    onSuccess: (updatedProject) => {
      queryClient.setQueryData(queryKeys.project.detail(project.uid), updatedProject)
    },
  })

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const { value } = event.target
    setProject({
      ...project,
      name: value,
    })
  }

  const handleMapperGroupsChange = (mapperGroups: string[]): void => {
    const updatedProject = { ...project, mapperGroups }
    setProject(updatedProject)
  }

  const baseHandleAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    const updatedAttributes = { ...project.attributes }
    updatedAttributes[tag] = attribute
    const updatedProject = { ...project, attributes: updatedAttributes }
    setProject(updatedProject)
  }
  return (
    <Grid
      container
      spacing={1}
      direction="column"
      justifyContent="flex-start"
      alignItems="flex-start"
    >
      <Grid size={{ xs: 6 }}>
        <Divider>
          <Chip label="General" color={'primary'} size="small" variant="outlined" />
        </Divider>
        <TextField
          label="Project Name"
          variant="standard"
          onChange={handleNameChange}
          defaultValue={project.name}
          autoFocus
          slotProps={{
            inputLabel: {
              shrink: true,
            },
          }}
        />
        <Divider>
          <Chip label="Mappers" color={'primary'} size="small" variant="outlined" />
        </Divider>
        <Spinner loading={mapperGroupsQuery.isLoading}>
          <MapperGroupSelect
            selectedMapperGroups={project.mapperGroups}
            availableMapperGroups={mapperGroupsQuery.data ?? []}
            setSelectedMapperGroups={handleMapperGroupsChange}
          />
        </Spinner>
        <Divider>
          <Chip label="Attributes" color={'primary'} size="small" variant="outlined" />
        </Divider>
        <AttributeDetails
          schemas={rootSchema?.project.attributes ?? {}}
          attributes={project.attributes}
          action={ItemDetailAction.EDIT}
          handleAttributeOpen={() => {}}
          handleAttributeUpdate={baseHandleAttributeUpdate}
        />

        {project.uid === '' ? (
          <Button onClick={handleCreateProject}>Create</Button>
        ) : (
          <Button onClick={() => projectUpdateMutation.mutate(project)}>Update</Button>
        )}
      </Grid>
    </Grid>
  )
}
