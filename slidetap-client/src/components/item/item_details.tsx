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

import {
  Button,
  Card,
  CardActions,
  CardContent,
  LinearProgress,
  Stack,
} from '@mui/material'
import Grid from '@mui/material/Grid2'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import Thumbnail from 'src/components/project/validate/thumbnail'
import { ValidateImage } from 'src/components/project/validate/validate_image'
import Spinner from 'src/components/spinner'
import { Action } from 'src/models/action'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import { isImageItem } from 'src/models/helpers'
import type { Image, Item } from 'src/models/item'
import { ItemValueType } from 'src/models/item_value_type'
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import itemApi from 'src/services/api/item_api'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import AttributeDetails from '../attribute/attribute_details'
import NestedAttributeDetails from '../attribute/nested_attribute_details'
import DisplayPreview from './display_preview'
import DisplayItemIdentifiers from './item_identifiers'
import DisplayItemStatus from './item_status'
import ItemLinkage from './linkage/item_linkage'

interface DisplayItemDetailsProps {
  itemUid: string | undefined
  itemSchemaUid: string | undefined
  projectUid: string
  batchUid: string | undefined
  action: Action.VIEW | Action.EDIT | Action.NEW | Action.COPY
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  setItemUid: React.Dispatch<React.SetStateAction<string | undefined>>
  setItemAction: React.Dispatch<
    React.SetStateAction<Action.VIEW | Action.EDIT | Action.NEW | Action.COPY>
  >
}

export default function DisplayItemDetails({
  itemUid,
  itemSchemaUid,
  projectUid,
  batchUid,
  action,
  setOpen,
  setItemUid,
  setItemAction,
}: DisplayItemDetailsProps): ReactElement {
  const queryClient = useQueryClient()
  const rootSchema = useSchemaContext()
  const [openedAttributes, setOpenedAttributes] = useState<
    Array<{
      schema: AttributeSchema
      attribute: Attribute<AttributeValueTypes>
      updateAttribute: (
        tag: string,
        attribute: Attribute<AttributeValueTypes>,
      ) => Attribute<AttributeValueTypes>
    }>
  >([])
  const [imageOpen, setImageOpen] = useState(false)
  const [openedImage, setOpenedImage] = useState<Image>()
  const [showPreview, setShowPreview] = useState(false)
  const itemQuery = useQuery({
    queryKey: ['item', itemUid, itemSchemaUid, action],
    queryFn: async () => {
      if (
        itemUid === undefined ||
        itemSchemaUid === undefined ||
        batchUid === undefined
      ) {
        return undefined
      }
      if (action === Action.NEW) {
        return await itemApi.create(itemSchemaUid, projectUid, batchUid)
      }
      if (action === Action.COPY) {
        return await itemApi.copy(itemUid)
      }
      if (action === Action.VIEW || action === Action.EDIT) {
        return await itemApi.get(itemUid)
      }
    },
    enabled: itemUid !== undefined,
  })

  const changeAction = (action: Action): void => {
    const openedAttributesToRestore = openedAttributes
    if (action !== Action.NEW && action !== Action.VIEW && action !== Action.EDIT) {
      return
    }
    setItemAction(action)
    setOpenedAttributes(openedAttributesToRestore)
  }

  const handleAttributeOpen = (
    schema: AttributeSchema,
    attribute: Attribute<AttributeValueTypes>,
    updateAttribute: (
      tag: string,
      attribute: Attribute<AttributeValueTypes>,
    ) => Attribute<AttributeValueTypes>,
  ): void => {
    setOpenedAttributes([...openedAttributes, { schema, attribute, updateAttribute }])
  }

  const save = async ({
    item,
    action,
  }: {
    item: Item
    action: Action
  }): Promise<Item> => {
    let savedItem: Promise<Item>
    if (action === Action.NEW || action === Action.COPY) {
      savedItem = itemApi.add(item)
    } else {
      savedItem = itemApi.save(item)
    }
    return await savedItem
  }

  const saveMutation = useMutation({
    mutationFn: save,
    onSuccess: (data) => {
      setItem(data)
      changeAction(Action.VIEW)
    },
  })

  const handleSave = (): void => {
    if (itemQuery.data === undefined) {
      return
    }
    saveMutation.mutate({ item: itemQuery.data, action })
  }

  const setItem = (item: Item): void => {
    queryClient.setQueryData<Item>(
      ['item', itemUid, itemSchemaUid, action],
      (oldData) => {
        return { ...oldData, ...item }
      },
    )
  }

  const baseHandleAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    if (itemQuery.data === undefined) {
      return
    }
    const updatedAttributes = { ...itemQuery.data.attributes }
    updatedAttributes[tag] = attribute
    const updatedItem = { ...itemQuery.data, attributes: updatedAttributes }
    setItem(updatedItem)
  }

  const handleSelectedUpdate = (selected: boolean): void => {
    if (itemQuery.data === undefined) {
      return
    }
    const updatedItem = { ...itemQuery.data }
    updatedItem.selected = selected
    setItem(updatedItem)
  }

  const handleIdentifierUpdate = (identifier: string): void => {
    if (itemQuery.data === undefined) {
      return
    }
    const updatedItem = { ...itemQuery.data }
    updatedItem.identifier = identifier
    setItem(updatedItem)
  }

  const handleNameUpdate = (name: string): void => {
    if (itemQuery.data === undefined) {
      return
    }
    const updatedItem = { ...itemQuery.data }
    updatedItem.name = name
    setItem(updatedItem)
  }

  const handleNestedAttributeChange = (uid?: string): void => {
    if (uid === undefined) {
      setOpenedAttributes([])
      return
    }
    const parentAttributeIndex = openedAttributes.findIndex(
      (attribute) => attribute.attribute.uid === uid,
    )
    if (parentAttributeIndex >= 0) {
      setOpenedAttributes(openedAttributes.slice(0, parentAttributeIndex + 1))
    }
  }

  function handleOpenImageChange(image: Image): void {
    setOpenedImage(image)
    setImageOpen(true)
  }

  if (itemQuery.data === undefined) {
    if (itemQuery.isLoading) {
      return <LinearProgress />
    } else {
      return <></>
    }
  }
  const itemSchema = (function () {
    switch (itemQuery.data.itemValueType) {
      case ItemValueType.SAMPLE:
        return rootSchema.samples[itemQuery.data.schemaUid]
      case ItemValueType.IMAGE:
        return rootSchema.images[itemQuery.data.schemaUid]
      case ItemValueType.OBSERVATION:
        return rootSchema.observations[itemQuery.data.schemaUid]
      case ItemValueType.ANNOTATION:
        return rootSchema.annotations[itemQuery.data.schemaUid]
      default:
        throw new Error('Unknown item value type')
    }
  })()

  return (
    <Spinner loading={itemQuery.isLoading}>
      <Card style={{ maxHeight: '80vh', overflowY: 'auto' }}>
        <CardContent>
          <Grid container spacing={1}>
            {openedAttributes.length === 0 && (
              <Grid size={{ xs: 12 }}>
                <Stack spacing={1}>
                  <DisplayItemIdentifiers
                    item={itemQuery.data}
                    action={action}
                    handleIdentifierUpdate={handleIdentifierUpdate}
                    handleNameUpdate={handleNameUpdate}
                  />
                  <DisplayItemStatus
                    item={itemQuery.data}
                    action={action}
                    handleSelectedUpdate={handleSelectedUpdate}
                  />

                  <ItemLinkage
                    item={itemQuery.data}
                    action={action}
                    handleItemOpen={(itemUid: string) => setItemUid(itemUid)}
                    setItem={setItem}
                  />

                  {isImageItem(itemQuery.data) && (
                    <Thumbnail
                      image={itemQuery.data}
                      openImage={handleOpenImageChange}
                      size={{ width: 512, height: 512 }}
                    />
                  )}
                  <AttributeDetails
                    schemas={itemSchema.attributes}
                    attributes={itemQuery.data.attributes}
                    action={action}
                    handleAttributeOpen={handleAttributeOpen}
                    handleAttributeUpdate={baseHandleAttributeUpdate}
                  />
                </Stack>
              </Grid>
            )}
            {openedAttributes.length > 0 && (
              <Grid size={{ xs: 12 }}>
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  action={action}
                  handleNestedAttributeChange={handleNestedAttributeChange}
                  handleAttributeOpen={handleAttributeOpen}
                  handleAttributeUpdate={baseHandleAttributeUpdate}
                />
              </Grid>
            )}
            <Grid size={{ xs: 12 }}>
              <DisplayPreview
                showPreview={showPreview}
                setShowPreview={setShowPreview}
                itemUid={itemQuery.data.uid}
              />
            </Grid>
          </Grid>
        </CardContent>
        <CardActions>
          {action === Action.VIEW && (
            <Button
              onClick={() => {
                changeAction(Action.EDIT)
              }}
            >
              Edit
            </Button>
          )}
          {(action === Action.EDIT ||
            action === Action.COPY ||
            action === Action.NEW) && (
            <React.Fragment>
              <Button
                onClick={() => {
                  changeAction(Action.VIEW)
                }}
              >
                Cancel
              </Button>

              <Button onClick={handleSave}>Save</Button>
            </React.Fragment>
          )}
          <Button onClick={() => setOpen(false)}>Close</Button>
        </CardActions>
      </Card>

      {openedImage !== undefined && (
        <ValidateImage open={imageOpen} image={openedImage} setOpen={setImageOpen} />
      )}
    </Spinner>
  )
}
