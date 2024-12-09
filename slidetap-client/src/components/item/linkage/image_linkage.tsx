import { Card, CardContent, CircularProgress, Stack, TextField } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Action } from 'models/action'
import { ImageStatusStrings } from 'models/image_status'
import { Image } from 'models/item'
import { ImageSchema } from 'models/schema/item_schema'
import { ReactElement } from 'react'
import schemaApi from 'services/api/schema_api'
import DisplayImageAnnotations from '../reference/display_image_annotations'
import DisplayImageObservations from '../reference/display_image_observations'
import DisplayImageRelations from '../reference/display_image_samples'

interface ImageLinkageProps {
  item: Image
  action: Action
  handleItemOpen: (itemUid: string) => void
  setItem: (value: Image) => void
}

export default function ImageLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: ImageLinkageProps): ReactElement {
  const schemaQuery = useQuery({
    queryKey: ['itemSchema', item.schemaUid],
    queryFn: async () => {
      return await schemaApi.getItemSchema<ImageSchema>(item.schemaUid)
    },
  })
  const handleImageSamplesUpdate = (references: string[]): void => {
    const updatedItem = { ...item, samples: references }
    setItem(updatedItem)
  }
  const handleImageAnnotationsUpdate = (references: string[]): void => {
    const updatedItem = { ...item, observations: references }
    setItem(updatedItem)
  }
  const handleImageObservationsUpdate = (references: string[]): void => {
    const updatedItem = { ...item, observations: references }
    setItem(updatedItem)
  }
  if (schemaQuery.isLoading || schemaQuery.data === undefined) {
    return <CircularProgress />
  }
  return (
    <Card>
      <CardContent>
        <Stack direction="column" spacing={1}>
          <TextField label="Status" value={ImageStatusStrings[item.status]} />
          <DisplayImageRelations
            action={action}
            relations={schemaQuery.data.samples}
            references={item.samples}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleImageSamplesUpdate}
          />
          <DisplayImageAnnotations
            action={action}
            relations={schemaQuery.data.annotations}
            references={item.samples}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleImageAnnotationsUpdate}
          />
          <DisplayImageObservations
            action={action}
            relations={schemaQuery.data.observations}
            references={item.samples}
            projectUid={item.projectUid}
            handleItemOpen={handleItemOpen}
            handleItemReferencesUpdate={handleImageObservationsUpdate}
          />
        </Stack>
      </CardContent>
    </Card>
  )
}
