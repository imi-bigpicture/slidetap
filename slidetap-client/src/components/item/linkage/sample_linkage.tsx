import { Stack } from '@mui/material'
import { ReactElement } from 'react'
import { ItemDetailAction } from 'src/models/action'
import { Sample } from 'src/models/item'
import DisplaySampleChildren from '../reference/display_sample_children'
import DisplaySampleImages from '../reference/display_sample_images'
import DisplaySampleObservations from '../reference/display_sample_observations'
import DisplaySampleParents from '../reference/display_sample_parents'

interface SampleLinkageProps {
  item: Sample
  action: ItemDetailAction
  handleItemOpen: (name: string, uid: string) => void
  setItem: (value: Sample) => void
}

export default function SampleLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: SampleLinkageProps): ReactElement {
  const handleSampleParentsUpdate = (
    schema_uid: string,
    references: string[],
  ): void => {
    const updatedItem = {
      ...item,
      parents: {
        ...item.parents,
        [schema_uid]: references,
      },
    }
    setItem(updatedItem)
  }
  const handleSampleChildrenUpdate = (
    schema_uid: string,
    references: string[],
  ): void => {
    const updatedItem = {
      ...item,
      children: {
        ...item.children,
        [schema_uid]: references,
      },
    }
    setItem(updatedItem)
  }
  const handleSampleImagesUpdate = (schema_uid: string, references: string[]): void => {
    const updatedItem = {
      ...item,
      images: {
        ...item.images,
        [schema_uid]: references,
      },
    }
    setItem(updatedItem)
  }
  const handleSampleObservationsUpdate = (
    schema_uid: string,
    references: string[],
  ): void => {
    const updatedItem = {
      ...item,
      observations: {
        ...item.observations,
        [schema_uid]: references,
      },
    }
    setItem(updatedItem)
  }

  return (
    <Stack direction="column" spacing={1}>
      <DisplaySampleParents
        action={action}
        schemaUid={item.schemaUid}
        references={item.parents}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleSampleParentsUpdate}
      ></DisplaySampleParents>
      <DisplaySampleChildren
        action={action}
        schemaUid={item.schemaUid}
        references={item.children}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleSampleChildrenUpdate}
      />
      <DisplaySampleImages
        action={action}
        schemaUid={item.schemaUid}
        references={item.images}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleSampleImagesUpdate}
      />
      <DisplaySampleObservations
        action={action}
        schemaUid={item.schemaUid}
        references={item.observations}
        datasetUid={item.datasetUid}
        batchUid={item.batchUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleSampleObservationsUpdate}
      />
    </Stack>
  )
}
