import { Stack, TextField } from '@mui/material'
import { ReactElement } from 'react'
import { ItemDetailAction } from 'src/models/action'
import { ImageStatusStrings } from 'src/models/image_status'
import { Image } from 'src/models/item'
import DisplayImageAnnotations from '../reference/display_image_annotations'
import DisplayImageObservations from '../reference/display_image_observations'
import DisplayImageRelations from '../reference/display_image_samples'

interface ImageLinkageProps {
  item: Image
  action: ItemDetailAction
  handleItemOpen: (name: string, uid: string) => void
  setItem: (value: Image) => void
}

export default function ImageLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: ImageLinkageProps): ReactElement {
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

  return (
    <Stack direction="column" spacing={1}>
      <TextField label="Status" value={ImageStatusStrings[item.status]} />
      <DisplayImageRelations
        action={action}
        schemaUid={item.schemaUid}
        references={item.samples}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleImageSamplesUpdate}
      />
      <DisplayImageAnnotations
        action={action}
        schemaUid={item.schemaUid}
        references={item.samples}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleImageAnnotationsUpdate}
      />
      <DisplayImageObservations
        action={action}
        schemaUid={item.schemaUid}
        references={item.samples}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleImageObservationsUpdate}
      />
    </Stack>
  )
}
