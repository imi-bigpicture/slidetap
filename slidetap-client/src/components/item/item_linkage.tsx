import { Card, CardContent, Stack, TextField } from '@mui/material'
import type { Item, ItemReference } from 'models/item'
import React, { type ReactElement } from 'react'

import { isImageItem, isSampleItem } from 'models/helpers'
import { ImageStatusStrings } from 'models/status'
import type { Action } from 'models/table_item'
import DisplayImageAnnotations from './reference/display_image_annotations'
import DisplayImageRelations from './reference/display_image_samples'
import DisplayImageObservations from './reference/display_image_samples copy'
import DisplaySampleChildren from './reference/display_sample_children'
import DisplaySampleImages from './reference/display_sample_images'
import DisplaySampleObservations from './reference/display_sample_observations'
import DisplaySampleParents from './reference/display_sample_parents'

interface ItemLinkageProps {
  item: Item
  action: Action
  handleItemOpen: (itemUid: string) => void
  setItem: (value: React.SetStateAction<Item | undefined>) => void
}

export default function ItemLinkage({
  item,
  action,
  handleItemOpen,
  setItem,
}: ItemLinkageProps): ReactElement {
  if (isSampleItem(item)) {
    const handleSampleParentsUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, parents: references }
      setItem(updatedItem)
    }
    const handleSampleChildrenUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, children: references }
      setItem(updatedItem)
    }
    const handleSampleImagesUpdate = (references: ItemReference[]): void => {
      console.log('adding image references', references)
      const updatedItem = { ...item, images: references }
      setItem(updatedItem)
    }
    const handleSampleObservationsUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, observations: references }
      setItem(updatedItem)
    }
    console.log(item.children, item.schema.children)
    return (
      <Card>
        <CardContent>
          <Stack direction="column" spacing={1}>
            <DisplaySampleParents
              action={action}
              relations={item.schema.parents}
              references={item.parents}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleSampleParentsUpdate}
            ></DisplaySampleParents>
            <DisplaySampleChildren
              action={action}
              relations={item.schema.children}
              references={item.children}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleSampleChildrenUpdate}
            />
            <DisplaySampleImages
              action={action}
              relations={item.schema.images}
              references={item.images}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleSampleImagesUpdate}
            />
            <DisplaySampleObservations
              action={action}
              relations={item.schema.observations}
              references={item.observations}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleSampleObservationsUpdate}
            />
          </Stack>
        </CardContent>
      </Card>
    )
  }
  if (isImageItem(item)) {
    const handleImageSamplesUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, samples: references }
      setItem(updatedItem)
    }
    const handleImageAnnotationsUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, observations: references }
      setItem(updatedItem)
    }
    const handleImageObservationsUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, observations: references }
      setItem(updatedItem)
    }
    return (
      <Card>
        <CardContent>
          <Stack direction="column" spacing={1}>
            <TextField label="Status" value={ImageStatusStrings[item.status]} />
            <DisplayImageRelations
              action={action}
              relations={item.schema.samples}
              references={item.samples}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleImageSamplesUpdate}
            />
            <DisplayImageAnnotations
              action={action}
              relations={item.schema.annotations}
              references={item.samples}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleImageAnnotationsUpdate}
            />
            <DisplayImageObservations
              action={action}
              relations={item.schema.observations}
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
  // if (isObservationItem(item)) {
  //   const handleObservationItemsUpdate = (references: ItemReference[]): void => {
  //     const updatedItem = { ...item, items: references }
  //     setItem(updatedItem)
  //   }
  //   const relation = [
  //     ...item.schema.samples,
  //     ...item.schema.images,
  //     ...item.schema.annotations,
  //   ].find((schema) => schema.uid === item.schema.uid)
  //   if (relation === undefined) {
  //     return <></>
  //   }

  //   if (!isObservationRelation(relation)) {
  //     throw new Error('Invalid observation relation')
  //   }

  //   return (
  //     <Card>
  //       <CardContent>
  //         <DisplayObservationRelations
  //           action={action}
  //           relation={relation}
  //           references={[item.item]}
  //           projectUid={item.projectUid}
  //           handleItemOpen={handleItemOpen}
  //           handleItemReferencesUpdate={handleObservationItemsUpdate}
  //         />
  //       </CardContent>
  //     </Card>
  //   )
  // }
  return <></>
}
