import { Card, CardContent, Stack, TextField } from '@mui/material'
import type { ItemDetails, ItemReference } from 'models/item'
import React, { type ReactElement } from 'react'

import type { Action } from 'models/action'
import {
  isImageItem,
  isObservationItem,
  isObservationToAnnotationRelation,
  isObservationToImageRelation,
  isObservationToSampleRelation,
  isSampleItem,
} from 'models/helpers'
import { ImageStatusStrings } from 'models/status'

import DisplayImageAnnotations from './reference/display_image_annotations'
import DisplayImageObservations from './reference/display_image_observations'
import DisplayImageRelations from './reference/display_image_samples'
import DisplayObservationAnnotation from './reference/display_observation_annotation'
import DisplayObservationImage from './reference/display_observation_image'
import DisplayObservationSample from './reference/display_observation_sample'
import DisplaySampleChildren from './reference/display_sample_children'
import DisplaySampleImages from './reference/display_sample_images'
import DisplaySampleObservations from './reference/display_sample_observations'
import DisplaySampleParents from './reference/display_sample_parents'

interface ItemLinkageProps {
  item: ItemDetails
  action: Action
  handleItemOpen: (itemUid: string) => void
  setItem: (value: React.SetStateAction<ItemDetails | undefined>) => void
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
      const updatedItem = { ...item, images: references }
      setItem(updatedItem)
    }
    const handleSampleObservationsUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, observations: references }
      setItem(updatedItem)
    }
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
  if (isObservationItem(item)) {
    const handleObservationItemsUpdate = (references: ItemReference[]): void => {
      const updatedItem = { ...item, item: references[0] }
      setItem(updatedItem)
    }
    const relation = [
      ...item.schema.samples,
      ...item.schema.images,
      ...item.schema.annotations,
    ].find((relation) => {
      if (isObservationToAnnotationRelation(relation)) {
        return relation.annotation.uid === item.item.schemaUid
      }
      if (isObservationToImageRelation(relation)) {
        return relation.image.uid === item.item.schemaUid
      }
      if (isObservationToSampleRelation(relation)) {
        return relation.sample.uid === item.item.schemaUid
      }
      return false
    })
    if (relation === undefined) {
      return <></>
    }
    if (isObservationToSampleRelation(relation)) {
      return (
        <Card>
          <CardContent>
            <DisplayObservationSample
              action={action}
              relation={relation}
              references={[item.item]}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleObservationItemsUpdate}
            />
          </CardContent>
        </Card>
      )
    }
    if (isObservationToImageRelation(relation)) {
      return (
        <Card>
          <CardContent>
            <DisplayObservationImage
              action={action}
              relation={relation}
              references={[item.item]}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleObservationItemsUpdate}
            />
          </CardContent>
        </Card>
      )
    }
    if (isObservationToAnnotationRelation(relation)) {
      return (
        <Card>
          <CardContent>
            <DisplayObservationAnnotation
              action={action}
              relation={relation}
              references={[item.item]}
              projectUid={item.projectUid}
              handleItemOpen={handleItemOpen}
              handleItemReferencesUpdate={handleObservationItemsUpdate}
            />
          </CardContent>
        </Card>
      )
    }

    throw new Error('Invalid observation relation')
  }
  return <></>
}
