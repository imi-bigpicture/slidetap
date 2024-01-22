import type { Project } from 'models/project'
import { ItemType } from 'models/schema'
import { ImageStatus, ImageStatusStrings } from 'models/status'
import React, { useEffect, type ReactElement } from 'react'

import { Box, Chip, Typography } from '@mui/material'
import LinearProgress, { type LinearProgressProps } from '@mui/material/LinearProgress'
import StepHeader from 'components/step_header'
import { Table } from 'components/table'
import type { Image } from 'models/table_item'
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

export default function Progress({ project }: ProgressProps): ReactElement {
  const [images, setImages] = React.useState<Image[]>([])
  const [progress, setProgress] = React.useState(0)
  useEffect(() => {
    const getImages = (): void => {
      itemApi
        .getItems<Image>(
          project.items.filter(
            (itemSchema) => itemSchema.schema.itemValueType === ItemType.IMAGE,
          )[0].schema.uid,
          project.uid,
          undefined,
        )
        .then(({ items, count }) => {
          const completed = items.filter(
            (image) => image.status === ImageStatus.POST_PROCESSED,
          )
          setProgress((100 * completed.length) / items.length)
          setImages(items)
        })
        .catch((x) => {
          console.error('Failed to get images', x)
        })
    }
    getImages()
    const intervalId = setInterval(() => {
      getImages()
    }, 2000)
    return () => {
      clearInterval(intervalId)
    }
  }, [project])

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

  return (
    <React.Fragment>
      <StepHeader title="Progress" description="Status of image export." />
      <LinearProgressWithLabel value={progress} />
      {images !== undefined && (
        <Table
          columns={[
            {
              header: 'Name',
              accessorKey: 'name',
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
          data={images.map((image) => {
            return {
              uid: image.uid,
              name: image.name,
              status: statusColumnFunction(image),
              statusMessage: image.statusMessage,
              attributes: [],
            }
          })}
          rowsSelectable={false}
        />
      )}
    </React.Fragment>
  )
}
