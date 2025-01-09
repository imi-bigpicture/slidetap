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

import { Chip, Grid, LinearProgress, Stack, Tooltip } from '@mui/material'
import Button from '@mui/material/Button'
import { useQuery } from '@tanstack/react-query'
import StepHeader from 'components/step_header'
import { ImageTable } from 'components/table/image_table'
import { ImageAction } from 'models/action'
import { ImageStatus, ImageStatusList, ImageStatusStrings } from 'models/image_status'
import { Image } from 'models/item'
import type { Project } from 'models/project'
import { ProjectStatus } from 'models/project_status'
import type { ColumnFilter, ColumnSort, TableItem } from 'models/table_item'
import React, { type ReactElement } from 'react'
import itemApi from 'services/api/item_api'
import projectApi from 'services/api/project_api'
import { useSchemaContext } from '../../contexts/schema_context'
import DisplayProjectValidation from './display_project_validation'

interface ProcessImagesProps {
  project: Project
  setProject: (project: Project) => void
}

function ProcessImages({ project, setProject }: ProcessImagesProps): ReactElement {
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid xs={12}>
        <StepHeader
          title="Process"
          description={
            project.status === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
              ? 'Process images in project.'
              : 'Status of image processing.'
          }
        />{' '}
      </Grid>
      {project.status === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE ? (
        <StartProcessImages project={project} setProject={setProject} />
      ) : (
        <ProcessImagesProgress project={project} />
      )}
    </Grid>
  )
}

export default ProcessImages

interface StartProcessImagesProps {
  project: Project
  setProject: (project: Project) => void
}

function StartProcessImages({
  project,
  setProject,
}: StartProcessImagesProps): React.ReactElement {
  const [starting, setStarting] = React.useState(false)
  const validationQuery = useQuery({
    queryKey: ['validation', project.uid],
    queryFn: async () => {
      return await projectApi.getValidation(project.uid)
    },
  })

  const handleStartProject = (e: React.MouseEvent<HTMLElement>): void => {
    setStarting(true)
    projectApi
      .process(project.uid)
      .then((updatedProject) => {
        setProject(updatedProject)
      })
      .catch((x) => {
        console.error('Failed to start project', x)
      })
  }
  if (validationQuery.data === undefined) {
    return <LinearProgress />
  }
  const isNotValid = validationQuery.data === undefined || !validationQuery.data.valid
  return (
    <Grid xs={4}>
      <Stack spacing={2}>
        {/* {project.items.map((itemSchema, index) => (
          <TextField
            key={index}
            label={itemSchema.schema.name}
            value={itemSchema.count}
            InputProps={{ readOnly: true }}
          />
        ))} */}
        <Tooltip
          title={
            isNotValid ? 'Project contains items that are not yet valid' : undefined
          }
        >
          <Stack>
            <Button disabled={isNotValid || starting} onClick={handleStartProject}>
              Start
            </Button>
          </Stack>
        </Tooltip>
      </Stack>
      {isNotValid &&
        validationQuery.data !== undefined &&
        DisplayProjectValidation({ validation: validationQuery.data })}
    </Grid>
  )
}

interface ProcessImagesProgressProps {
  project: Project
}

function ProcessImagesProgress({
  project,
}: ProcessImagesProgressProps): React.ReactElement {
  const rootSchema = useSchemaContext()

  const statusColumnFunction = (image: Image): ReactElement => {
    if (image.status === ImageStatus.POST_PROCESSED) {
      return (
        <Chip
          label={ImageStatusStrings[image.status]}
          color="success"
          variant="outlined"
        />
      )
    }
    if (image.status === ImageStatus.POST_PROCESSING_FAILED) {
      return (
        <Chip
          label={ImageStatusStrings[image.status]}
          color="error"
          variant="outlined"
        />
      )
    }
    if (image.status === ImageStatus.PRE_PROCESSED) {
      return (
        <Chip
          label={ImageStatusStrings[image.status]}
          color="secondary"
          variant="outlined"
        />
      )
    }
    return (
      <Chip
        label={ImageStatusStrings[image.status]}
        color="primary"
        variant="outlined"
      />
    )
  }

  const getImages = async (
    start: number,
    size: number,
    filters: ColumnFilter[],
    sorting: ColumnSort[],
  ): Promise<{ items: TableItem[]; count: number }> => {
    const request = {
      start,
      size,
      identifierFilter: filters.find((filter) => filter.id === 'id')?.value as string,
      attributeFilters:
        filters.length > 0
          ? filters
              .filter((filter) => filter.id.startsWith('attributes.'))
              .reduce<Record<string, string>>(
                (attributeFilters, filter) => ({
                  ...attributeFilters,
                  [filter.id.split('attributes.')[1]]: String(filter.value),
                }),
                {},
              )
          : undefined,
      sorting: sorting.length > 0 ? sorting : undefined,
      statusFilter: (
        filters.find((filter) => filter.id === 'status')?.value as string[]
      ).map((value) => parseInt(value)),
    }
    return await itemApi
      .getItems<Image>(Object.values(rootSchema.images)[0].uid, project.uid, request)
      .then(({ items, count }) => {
        return {
          items: items.map((image) => {
            return {
              uid: image.uid,
              identifier: image.identifier,
              name: image.name,
              status: image.status,
              statusMessage: image.statusMessage,
              attributes: [],
            }
          }),
          count,
        }
      })
  }
  const handleImageAction = (imageUid: string, action: ImageAction): void => {
    if (action === ImageAction.DELETE || action === ImageAction.RESTORE) {
      itemApi.select(imageUid, action === ImageAction.RESTORE).catch((x) => {
        console.error('Failed to select image', x)
      })
    } else if (action === ImageAction.RETRY) {
      itemApi.retry([imageUid]).catch((x) => {
        console.error('Failed to retry image', x)
      })
    }
  }
  const handleImagesRetry = (imageUids: string[]): void => {
    itemApi.retry(imageUids).catch((x) => {
      console.error('Failed to retry images', x)
    })
  }
  return (
    <Grid xs={12}>
      <ImageTable
        getItems={getImages}
        columns={[
          {
            id: 'id',
            header: 'Identifier',
            accessorKey: 'identifier',
          },
          {
            id: 'name',
            header: 'Status',
            accessorKey: 'status',
            Cell: ({ renderedCellValue, row }) => statusColumnFunction(row.original),
            filterVariant: 'multi-select',
            filterSelectOptions: ImageStatusList.map((status) => ({
              label: ImageStatusStrings[status],
              value: status.toString(),
            })),
          },
          {
            id: 'status',
            header: 'Message',
            accessorKey: 'statusMessage',
          },
        ]}
        rowsSelectable={true}
        onRowAction={handleImageAction}
        onRowsRetry={handleImagesRetry}
      />
    </Grid>
  )
}
