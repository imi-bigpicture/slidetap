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

import { Chip, Stack } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Grid2'
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

interface PreProcessImagesProps {
  project: Project
  setProject: (project: Project) => void
}

function PreProcessImages({
  project,
  setProject,
}: PreProcessImagesProps): React.ReactElement {
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid size={{ xs: 12 }}>
        <StepHeader
          title="Pre-process"
          description={
            project.status === ProjectStatus.METADATA_SEARCH_COMPLETE
              ? 'Pre-process images in project.'
              : 'Status of image pre-processing.'
          }
        />
      </Grid>
      {project.status === ProjectStatus.METADATA_SEARCH_COMPLETE ? (
        <StartPreProcessImages project={project} setProject={setProject} />
      ) : (
        <PreprocessImagesProgress project={project} />
      )}
    </Grid>
  )
}

export default PreProcessImages

interface StartPreProcessImagesProps {
  project: Project
  setProject: (project: Project) => void
}

function StartPreProcessImages({
  project,
  setProject,
}: StartPreProcessImagesProps): React.ReactElement {
  const [starting, setStarting] = React.useState(false)

  const handleStartPreProcessingImages = (e: React.MouseEvent<HTMLElement>): void => {
    setStarting(true)
    projectApi
      .preProcess(project.uid)
      .then((updatedProject) => {
        setProject(updatedProject)
      })
      .catch((x) => {
        console.error('Failed to download project', x)
      })
  }

  // TODO add count of items in project
  return (
    <Grid size={{ xs: 4 }}>
      <Stack spacing={2}>
        {/* {Object.values(rootSchemaQuery.data.samples).map((itemSchema, index) => (
          <TextField
            key={index}
            label={itemSchema.name}
            value={itemSchema.count}
            InputProps={{ readOnly: true }}
          />
        ))} */}
        <Button disabled={starting} onClick={handleStartPreProcessingImages}>
          Pre-process
        </Button>
      </Stack>
    </Grid>
  )
}

interface PreprocessImagesProgressProps {
  project: Project
}

function PreprocessImagesProgress({
  project,
}: PreprocessImagesProgressProps): React.ReactElement {
  const rootSchema = useSchemaContext()
  const statusColumnFunction = (image: Image): ReactElement => {
    if (image.status === ImageStatus.PRE_PROCESSED) {
      return (
        <Chip
          label={ImageStatusStrings[image.status]}
          color="success"
          variant="outlined"
        />
      )
    }
    if (image.status === ImageStatus.PRE_PROCESSING_FAILED) {
      return (
        <Chip
          label={ImageStatusStrings[image.status]}
          color="error"
          variant="outlined"
        />
      )
    }
    if (image.status === ImageStatus.NOT_STARTED) {
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
    const statusFilter = filters.find((filter) => filter.id === 'status')?.value
      ? (filters.find((filter) => filter.id === 'status')?.value as string[]).map(
          (status) => parseInt(status),
        )
      : undefined
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
      statusFilter: statusFilter,
    }
    return await itemApi
      .getItems<Image>(Object.values(rootSchema.images)[0].uid, project.uid, request)
      .then(({ items, count }) => {
        console.log('items', items)
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
    <Grid size={{ xs: 12 }}>
      <ImageTable
        getItems={getImages}
        columns={[
          {
            header: 'Identifier',
            accessorKey: 'identifier',
          },
          {
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
