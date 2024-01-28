import { Box, Chip, Typography } from '@mui/material'
import LinearProgress, { type LinearProgressProps } from '@mui/material/LinearProgress'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import StepHeader from 'components/step_header'
import { ImageTable } from 'components/table'
import type { Project } from 'models/project'
import { ItemType } from 'models/schema'
import { ImageStatus, ImageStatusStrings } from 'models/status'
import type { ColumnFilter, ColumnSort, Image, TableItem } from 'models/table_item'
import React, { type ReactElement } from 'react'
import itemApi from 'services/api/item_api'

interface ProgressProps {
  project: Project
}

function LinearProgressWithLabel(
  props: LinearProgressProps & { value: number },
): ReactElement {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center' }}>
      <Box sx={{ width: '100%', mr: 1 }}>
        <LinearProgress variant="determinate" {...props} />
      </Box>
      <Box sx={{ minWidth: 35 }}>
        <Typography variant="body2" color="text.secondary">{`${Math.round(
          props.value,
        )}%`}</Typography>
      </Box>
    </Box>
  )
}

export default function Progress({ project }: ProgressProps): React.ReactElement {
  // const [images, setImages] = React.useState<Image[]>([])
  // const [progress, setProgress] = React.useState(0)
  // useEffect(() => {
  //   const getImages = (): void => {
  //     itemApi
  //       .getItems<Image>(
  //         project.items.filter(
  //           (itemSchema) => itemSchema.schema.itemValueType === ItemType.IMAGE,
  //         )[0].schema.uid,
  //         project.uid,
  //         undefined,
  //       )
  //       .then(({ items, count }) => {
  //         const completed = items.filter(
  //           (image) => image.status === ImageStatus.POST_PROCESSED,
  //         )
  //         setProgress((100 * completed.length) / items.length)
  //         setImages(items)
  //       })
  //       .catch((x) => {
  //         console.error('Failed to get images', x)
  //       })
  //   }
  //   getImages()
  //   const intervalId = setInterval(() => {
  //     getImages()
  //   }, 2000)
  //   return () => {
  //     clearInterval(intervalId)
  //   }
  // }, [project])

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
              status: statusColumnFunction(image),
              statusMessage: image.statusMessage,
              attributes: [],
            }
          }),
          count,
        }
      })
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid xs={12}>
        <StepHeader title="Progress" description="Status of image export." />
      </Grid>
      <Grid xs={12}>
        {/* <LinearProgressWithLabel value={progress} /> */}
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
            },
            {
              header: 'Message',
              accessorKey: 'statusMessage',
            },
          ]}
          rowsSelectable={false}
        />
      </Grid>
    </Grid>
  )
}
