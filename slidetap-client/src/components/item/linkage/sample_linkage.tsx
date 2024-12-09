import { CircularProgress, Stack } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { Action } from 'models/action'
import { Sample } from 'models/item'
import { SampleSchema } from 'models/schema/item_schema'
import { ReactElement } from 'react'
import schemaApi from 'services/api/schema_api'
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
  const schemaQuery = useQuery({
    queryKey: ['itemSchema', item.schemaUid],
    queryFn: async () => {
      return await schemaApi.getItemSchema<SampleSchema>(item.schemaUid)
    },
  })
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
  if (schemaQuery.isLoading || schemaQuery.data === undefined) {
    return <CircularProgress />
  }
  return (
    <Stack direction="column" spacing={1}>
      <DisplaySampleParents
        action={action}
        relations={schemaQuery.data.parents}
        references={item.parents}
        projectUid={item.projectUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleSampleParentsUpdate}
      ></DisplaySampleParents>
      <DisplaySampleChildren
        action={action}
        relations={schemaQuery.data.children}
        references={item.children}
        projectUid={item.projectUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleSampleChildrenUpdate}
      />
      <DisplaySampleImages
        action={action}
        relations={schemaQuery.data.images}
        references={item.images}
        projectUid={item.projectUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleSampleImagesUpdate}
      />
      <DisplaySampleObservations
        action={action}
        relations={schemaQuery.data.observations}
        references={item.observations}
        projectUid={item.projectUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleSampleObservationsUpdate}
      />
    </Stack>
  )
}
