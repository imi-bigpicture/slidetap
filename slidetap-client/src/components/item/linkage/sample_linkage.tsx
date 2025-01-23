import { Stack } from '@mui/material'
import { ReactElement } from 'react'
import { Action } from 'src/models/action'
import { Sample } from 'src/models/item'
import DisplaySampleChildren from '../reference/display_sample_children'
import DisplaySampleImages from '../reference/display_sample_images'
import DisplaySampleObservations from '../reference/display_sample_observations'
import DisplaySampleParents from '../reference/display_sample_parents'

interface SampleLinkageProps {
  item: Sample
  action: Action
  handleItemOpen: (itemUid: string) => void
  setItem: (value: Sample) => void
}

export default function SampleLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: SampleLinkageProps): ReactElement {
  const handleSampleParentsUpdate = (references: string[]): void => {
    const updatedItem = { ...item, parents: references }
    setItem(updatedItem)
  }
  const handleSampleChildrenUpdate = (references: string[]): void => {
    const updatedItem = { ...item, children: references }
    setItem(updatedItem)
  }
  const handleSampleImagesUpdate = (references: string[]): void => {
    const updatedItem = { ...item, images: references }
    setItem(updatedItem)
  }
  const handleSampleObservationsUpdate = (references: string[]): void => {
    const updatedItem = { ...item, observations: references }
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
