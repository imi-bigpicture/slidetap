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
  CardHeader,
  LinearProgress,
  Stack,
} from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import Thumbnail from 'components/project/validate/thumbnail'
import { ValidateImage } from 'components/project/validate/validate_image'
import Spinner from 'components/spinner'
import { Action, ActionStrings } from 'models/action'
import type { Attribute } from 'models/attribute'
import { isImageItem } from 'models/helpers'
import type { ImageDetails, ItemDetails } from 'models/item'
import React, { useState, type ReactElement } from 'react'
import { useMutation, useQuery, useQueryClient } from 'react-query'
import itemApi from 'services/api/item_api'
import AttributeDetails from '../attribute/attribute_details'
import NestedAttributeDetails from '../attribute/nested_attribute_details'
import DisplayItemValidation from './display_item_validation'
import DisplayPreview from './display_preview'
import DisplayItemIdentifiers from './item_identifiers'
import ItemLinkage from './item_linkage'
import DisplayItemStatus from './item_status'

interface DisplayItemDetailsProps {
  itemUid: string | undefined
  itemSchemaUid: string | undefined
  projectUid: string
  action: Action.VIEW | Action.EDIT | Action.NEW | Action.COPY
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function DisplayItemDetails({
  itemUid: ititialItemUid,
  itemSchemaUid,
  projectUid,
  action: initialAction,
  setOpen,
}: DisplayItemDetailsProps): ReactElement {
  const queryClient = useQueryClient()
  const [itemUid, setItemUid] = useState<string | undefined>(ititialItemUid)
  const [openedAttributes, setOpenedAttributes] = useState<
    Array<{
      attribute: Attribute<any, any>
      updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>
    }>
  >([])
  const [action, setAction] = useState<Action>(initialAction)
  const [imageOpen, setImageOpen] = useState(false)
  const [openedImage, setOpenedImage] = useState<ImageDetails>()
  const [showPreview, setShowPreview] = useState(false)
  const itemQuery = useQuery({
    queryKey: ['item', itemUid, itemSchemaUid, action],
    queryFn: async () => {
      if (itemUid === undefined || itemSchemaUid === undefined) {
        return undefined
      }
      if (action === Action.NEW) {
        return await itemApi.create(itemSchemaUid, projectUid)
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
  const validationQuery = useQuery({
    queryKey: ['validation', itemUid, itemQuery.data],
    queryFn: async () => {
      if (itemUid === undefined) {
        return undefined
      }
      return await itemApi.getValidation(itemUid)
    },
    enabled: itemUid !== undefined,
  })

  const changeAction = (action: Action): void => {
    const openedAttributesToRestore = openedAttributes
    setAction(action)
    setOpenedAttributes(openedAttributesToRestore)
  }

  const handleAttributeOpen = (
    attribute: Attribute<any, any>,
    updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>,
  ): void => {
    setOpenedAttributes([...openedAttributes, { attribute, updateAttribute }])
  }

  const handleItemOpen = (itemUid: string): void => {
    setItemUid(itemUid)
  }

  const handleClose = (): void => {
    setOpen(false)
  }

  const save = async ({
    item,
    action,
  }: {
    item: ItemDetails
    action: Action
  }): Promise<ItemDetails> => {
    let savedItem: Promise<ItemDetails>
    if (action === Action.NEW || action === Action.COPY) {
      savedItem = itemApi.add(item, projectUid)
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

  const setItem = (item: ItemDetails): void => {
    console.log('setItem', item)
    queryClient.setQueryData<ItemDetails>(
      ['item', itemUid, itemSchemaUid, action],
      (oldData) => {
        return { ...oldData, ...item }
      },
    )
  }

  const baseHandleAttributeUpdate = (attribute: Attribute<any, any>): void => {
    if (itemQuery.data === undefined) {
      return
    }
    const updatedAttributes = { ...itemQuery.data.attributes }
    updatedAttributes[attribute.schema.tag] = attribute
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

  function handleOpenImageChange(image: ImageDetails): void {
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

  return (
    <Spinner loading={itemQuery.isLoading}>
      <Card style={{ maxHeight: '80vh', overflowY: 'auto' }}>
        <CardHeader
          title={
            ActionStrings[action] +
            ' ' +
            itemQuery.data.schema.displayName +
            ': ' +
            itemQuery.data.identifier
          }
        />
        <CardContent>
          <Grid container spacing={1}>
            {openedAttributes.length === 0 && (
              <Grid xs={12}>
                <Stack spacing={2}>
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
                    handleItemOpen={handleItemOpen}
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
                    schemas={itemQuery.data.schema.attributes}
                    attributes={itemQuery.data.attributes}
                    action={action}
                    handleAttributeOpen={handleAttributeOpen}
                    handleAttributeUpdate={baseHandleAttributeUpdate}
                  />
                </Stack>
              </Grid>
            )}
            {openedAttributes.length > 0 && (
              <Grid xs={12}>
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  action={action}
                  handleNestedAttributeChange={handleNestedAttributeChange}
                  handleAttributeOpen={handleAttributeOpen}
                  handleAttributeUpdate={baseHandleAttributeUpdate}
                />
              </Grid>
            )}
            <Grid xs={12}>
              <DisplayPreview
                showPreview={showPreview}
                setShowPreview={setShowPreview}
                itemUid={itemQuery.data.uid}
              />
            </Grid>
            <Grid xs={12}>
              {validationQuery.data !== undefined && (
                <DisplayItemValidation validation={validationQuery.data} />
              )}
            </Grid>
          </Grid>
        </CardContent>
        <CardActions disableSpacing>
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
          <Button onClick={handleClose}>Close</Button>
        </CardActions>
      </Card>

      {openedImage !== undefined && (
        <ValidateImage open={imageOpen} image={openedImage} setOpen={setImageOpen} />
      )}
    </Spinner>
  )
}
