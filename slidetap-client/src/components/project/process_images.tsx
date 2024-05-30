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

import { Chip, Stack, TextField, Tooltip } from '@mui/material'
import Button from '@mui/material/Button'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import StepHeader from 'components/step_header'
import { ImageTable } from 'components/table/image_table'
import { ImageAction } from 'models/action'
import type { Project } from 'models/project'
import { ItemType } from 'models/schema'
import { ImageStatus, ImageStatusStrings, ProjectStatus } from 'models/status'
import type { ColumnFilter, ColumnSort, Image, TableItem } from 'models/table_item'
import type { ProjectValidation } from 'models/validation'
import React, { useEffect, type ReactElement } from 'react'
import itemApi from 'services/api/item_api'
import projectApi from 'services/api/project_api'
import DisplayProjectValidation from './display_project_validation'

interface ProcessImagesProps {
  project: Project
  setProject: React.Dispatch<React.SetStateAction<Project | undefined>>
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
  setProject: React.Dispatch<React.SetStateAction<Project | undefined>>
}

function StartProcessImages({
  project,
  setProject,
}: StartProcessImagesProps): React.ReactElement {
  const [validation, setValidation] = React.useState<ProjectValidation>()
  const [starting, setStarting] = React.useState(false)
  useEffect(() => {
    const getValidation = (projectUid: string): void => {
      projectApi
        .getValidation(projectUid)
        .then((responseValidation) => {
          setValidation(responseValidation)
        })
        .catch((x) => {
          console.error('Failed to get validation', x)
        })
    }
    getValidation(project.uid)
  }, [project.uid])

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
  const isNotValid = validation === undefined || !validation.valid
  return (
    <Grid xs={4}>
      <Stack spacing={2}>
        {project.items.map((itemSchema, index) => (
          <TextField
            key={index}
            label={itemSchema.schema.name}
            value={itemSchema.count}
            InputProps={{ readOnly: true }}
          />
        ))}
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
        validation !== undefined &&
        DisplayProjectValidation({ validation })}
    </Grid>
  )
}

interface ProcessImagesProgressProps {
  project: Project
}

function ProcessImagesProgress({
  project,
}: ProcessImagesProgressProps): React.ReactElement {
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
    }
    return await itemApi
      .getItems<Image>(
        project.items.filter(
          (itemSchema) => itemSchema.schema.itemValueType === ItemType.IMAGE,
        )[0].schema.uid,
        project.uid,
        request,
      )
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
    console.log('Retrying images', imageUids)
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
