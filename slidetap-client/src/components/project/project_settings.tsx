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

import {
  Alert,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import AttributeDetails from 'src/components/attribute/attribute_details'
import { useError } from 'src/contexts/error/error_context'
import { ItemDetailAction } from 'src/models/action'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { Project } from 'src/models/project'
import { ProjectStatus } from 'src/models/project_status'
import { ApiError } from 'src/services/api/api_methods'
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

/** Which of the four the dialog is asking about, or neither. */
type PendingPseudonymAction = 'new' | 'clear' | 'identifiers' | 'seed' | null

/** What the server said it would not do, rather than that something failed. */
function refusal(error: Error | null): string | undefined {
  if (error === null) {
    return undefined
  }
  return error instanceof ApiError ? (error.body ?? error.message) : error.message
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

  const [pending, setPending] = React.useState<PendingPseudonymAction>(null)
  // Every item now says something else about itself, and the pseudonym is what
  // the tables show of it where the curator is reading pseudonyms.
  const invalidateItems = (): void => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
  }
  const repseudonymizeMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.repseudonymize(projectUid)
    },
    onSuccess: invalidateItems,
  })
  const clearPseudonymsMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.clearPseudonyms(projectUid)
    },
    onSuccess: invalidateItems,
  })
  const pseudonymizeIdentifiersMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.pseudonymizeIdentifiers(projectUid)
    },
    onSuccess: invalidateItems,
  })
  const clearSeedMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.clearSeed(projectUid)
    },
    onSuccess: (updatedProject) => {
      queryClient.setQueryData(queryKeys.project.detail(project.uid), updatedProject)
    },
  })
  const handleConfirmed = (): void => {
    const action = pending
    setPending(null)
    if (action === 'new') {
      repseudonymizeMutation.mutate(project.uid)
    } else if (action === 'clear') {
      clearPseudonymsMutation.mutate(project.uid)
    } else if (action === 'identifiers') {
      pseudonymizeIdentifiersMutation.mutate(project.uid)
    } else if (action === 'seed') {
      clearSeedMutation.mutate(project.uid)
    }
  }
  const isCompleted = project.status === ProjectStatus.COMPLETED
  const pseudonymsBusy =
    repseudonymizeMutation.isPending ||
    clearPseudonymsMutation.isPending ||
    pseudonymizeIdentifiersMutation.isPending ||
    clearSeedMutation.isPending

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
      sx={{ flexDirection: 'column', justifyContent: 'flex-start', alignItems: 'flex-start' }}
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
          attributeLayout={rootSchema?.project.attributeLayout}
          handleAttributeUpdate={baseHandleAttributeUpdate}
        />

        {project.uid === '' ? (
          <Button onClick={handleCreateProject}>Create</Button>
        ) : (
          <Button onClick={() => projectUpdateMutation.mutate(project)}>Update</Button>
        )}

        {project.uid !== '' && (
          <>
            <Divider>
              <Chip label="Pseudonyms" color={'primary'} size="small" variant="outlined" />
            </Divider>
            <Stack spacing={1}>
              <Typography variant="body2" color="text.secondary">
                The dataset goes out under the pseudonyms its items were given when
                they were imported, the same ones every time it is submitted. New ones
                are for a dataset that has to go out unlinkable to what went out
                before; submit it afterwards to write the metadata under them. Taking
                them off instead leaves the items standing for nothing that has gone
                out, and the project cannot be submitted again. Images already written
                to the outbox carry the pseudonyms they were written with either way.
                Clearing the importer seed stops any future import into this dataset
                from deriving item uids the way past ones were, without touching a
                single existing item.
              </Typography>
              <Tooltip
                title={
                  isCompleted
                    ? undefined
                    : 'Only a completed project can have its pseudonyms changed'
                }
              >
                <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
                  <Button
                    disabled={!isCompleted || pseudonymsBusy}
                    onClick={() => {
                      setPending('new')
                    }}
                  >
                    New pseudonyms
                  </Button>
                  <Button
                    color="error"
                    disabled={!isCompleted || pseudonymsBusy}
                    onClick={() => {
                      setPending('clear')
                    }}
                  >
                    Clear pseudonyms
                  </Button>
                  <Button
                    color="error"
                    disabled={!isCompleted || pseudonymsBusy}
                    onClick={() => {
                      setPending('identifiers')
                    }}
                  >
                    Replace identifiers with pseudonyms
                  </Button>
                  <Button
                    color="error"
                    disabled={!isCompleted || pseudonymsBusy}
                    onClick={() => {
                      setPending('seed')
                    }}
                  >
                    Clear importer seed
                  </Button>
                </Stack>
              </Tooltip>
              {repseudonymizeMutation.isSuccess && (
                <Alert severity="success">
                  {repseudonymizeMutation.data.changed} items were given a new
                  pseudonym. Submit the project to write the metadata under them.
                </Alert>
              )}
              {clearPseudonymsMutation.isSuccess && (
                <Alert severity="success">
                  {clearPseudonymsMutation.data.changed} items no longer carry a
                  pseudonym. The project can no longer be submitted.
                </Alert>
              )}
              {pseudonymizeIdentifiersMutation.isSuccess && (
                <Alert severity="success">
                  {pseudonymizeIdentifiersMutation.data.changed} items now have their
                  pseudonym as their identifier. What they were called before is gone.
                </Alert>
              )}
              {clearSeedMutation.isSuccess && (
                <Alert severity="success">
                  The importer seed is cleared. Future imports into this dataset fall
                  back to whatever the importer does without one.
                </Alert>
              )}
              {repseudonymizeMutation.isError && (
                <Alert severity="error">{refusal(repseudonymizeMutation.error)}</Alert>
              )}
              {clearPseudonymsMutation.isError && (
                <Alert severity="error">{refusal(clearPseudonymsMutation.error)}</Alert>
              )}
              {pseudonymizeIdentifiersMutation.isError && (
                <Alert severity="error">
                  {refusal(pseudonymizeIdentifiersMutation.error)}
                </Alert>
              )}
              {clearSeedMutation.isError && (
                <Alert severity="error">{refusal(clearSeedMutation.error)}</Alert>
              )}
            </Stack>
          </>
        )}
      </Grid>
      <Dialog
        open={pending !== null}
        onClose={() => {
          setPending(null)
        }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>
          {pending === 'clear'
            ? 'Take the pseudonyms off the dataset?'
            : pending === 'identifiers'
              ? 'Replace identifiers with pseudonyms?'
              : pending === 'seed'
                ? 'Clear the importer seed?'
                : 'Give the dataset new pseudonyms?'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {pending === 'clear' ? (
              <>
                Every item of <strong>{project.name}</strong> loses the pseudonym it
                went out under, and nothing puts one back: the project cannot be
                submitted again. What has already been handed over is not touched, and
                neither is the pseudonym file written beside it, which still maps what
                went out to what it was.
              </>
            ) : pending === 'identifiers' ? (
              <>
                Every item of <strong>{project.name}</strong> that has a pseudonym is
                known by it here from now on: its identifier is overwritten with the
                pseudonym, and there is no way back. An item without a pseudonym keeps
                the identifier it has.
              </>
            ) : pending === 'seed' ? (
              <>
                <strong>{project.name}</strong> loses the secret its importer derives
                item uids from, and nothing puts one back. Existing items are not
                touched -- only a future import into this dataset falls back to
                whatever the importer does without a seed.
              </>
            ) : (
              <>
                Every item of <strong>{project.name}</strong> is given a pseudonym it
                has not had before. What has already been submitted keeps the old ones,
                and nothing here says which new pseudonym took which old one&apos;s
                place.
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setPending(null)
            }}
          >
            Cancel
          </Button>
          <Button
            color={
              pending === 'clear' || pending === 'identifiers' || pending === 'seed'
                ? 'error'
                : 'primary'
            }
            onClick={handleConfirmed}
          >
            {pending === 'clear'
              ? 'Clear pseudonyms'
              : pending === 'identifiers'
                ? 'Replace identifiers'
                : pending === 'seed'
                  ? 'Clear seed'
                  : 'New pseudonyms'}
          </Button>
        </DialogActions>
      </Dialog>
    </Grid>
  )
}
