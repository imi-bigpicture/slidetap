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

import HomeIcon from '@mui/icons-material/Home'
import {
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardActions,
  CardContent,
  Divider,
  LinearProgress,
  Link,
  Stack,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid'

import { OpenInNew, PhotoLibrary, Preview, Security } from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import Thumbnail from 'src/components/project/validate/thumbnail'
import { ValidateImage } from 'src/components/project/validate/validate_image'
import Spinner from 'src/components/spinner'
import { ItemDetailAction } from 'src/models/action'
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
  projectUid: string
  itemUid: string
  action: ItemDetailAction
  privateOpen: boolean
  previewOpen: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  setItemUid: React.Dispatch<React.SetStateAction<string>>
  setItemAction: React.Dispatch<React.SetStateAction<ItemDetailAction>>
  setPrivateOpen: React.Dispatch<React.SetStateAction<boolean>>
  setPreviewOpen: React.Dispatch<React.SetStateAction<boolean>>
  windowed: boolean
}

export default function DisplayItemDetails({
  projectUid,
  itemUid,
  action,
  privateOpen,
  previewOpen,
  setOpen,
  setItemUid,
  setItemAction,
  setPrivateOpen,
  setPreviewOpen,
  windowed,
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
  const [openedItems, setOpenedItems] = useState<
    Array<{
      identifier: string
      uid: string
    }>
  >([{ identifier: '', uid: itemUid }])
  const [imageOpen, setImageOpen] = useState(false)
  const [openedImage, setOpenedImage] = useState<Image>()
  const itemQuery = useQuery({
    queryKey: ['item', itemUid, action],
    queryFn: async () => {
      if (action === ItemDetailAction.COPY) {
        return await itemApi.copy(itemUid)
      }
      if (action === ItemDetailAction.VIEW || action === ItemDetailAction.EDIT) {
        return await itemApi.get(itemUid)
      }
    },
    enabled: itemUid !== undefined,
  })

  const changeAction = (action: ItemDetailAction): void => {
    const openedAttributesToRestore = openedAttributes
    if (action !== ItemDetailAction.VIEW && action !== ItemDetailAction.EDIT) {
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
    action: ItemDetailAction
  }): Promise<Item> => {
    let savedItem: Promise<Item>
    if (action === ItemDetailAction.COPY) {
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
      changeAction(ItemDetailAction.VIEW)
    },
  })

  const handleSave = (): void => {
    if (itemQuery.data === undefined) {
      return
    }
    saveMutation.mutate({ item: itemQuery.data, action })
  }

  const setItem = (item: Item): void => {
    queryClient.setQueryData<Item>(['item', itemUid, action], (oldData) => {
      return { ...oldData, ...item }
    })
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

  const handleChangeItem = (name: string, uid: string): void => {
    setItemUid(uid)
    const existingIndex = openedItems.findIndex((i) => i.uid === uid)
    console.log('existingIndex', existingIndex)
    if (existingIndex >= 0) {
      setOpenedItems(openedItems.slice(0, existingIndex + 1))
    } else {
      setOpenedItems([...openedItems, { identifier: name, uid: uid }])
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
          <Grid container spacing={4}>
            <Grid size="grow">
              {openedAttributes.length === 0 && (
                <Stack spacing={1}>
                  <Breadcrumbs aria-label="breadcrumb">
                    <Link
                      onClick={() => {
                        if (itemQuery.data !== undefined) {
                          const firstItem = openedItems[0]
                          setOpenedItems(openedItems.slice(0, 1))
                          setItemUid(firstItem.uid)
                        }
                      }}
                    >
                      <HomeIcon />
                    </Link>
                    {openedItems.slice(1).map((item) => {
                      return (
                        <Link
                          key={item.uid}
                          onClick={() => {
                            handleChangeItem(item.identifier, item.uid)
                          }}
                        >
                          {item.identifier}
                        </Link>
                      )
                    })}
                  </Breadcrumbs>
                  <Divider>
                    <Typography variant="h6">Item details</Typography>
                  </Divider>
                  <DisplayItemIdentifiers
                    item={itemQuery.data}
                    action={action}
                    handleIdentifierUpdate={handleIdentifierUpdate}
                    handleNameUpdate={handleNameUpdate}
                  />
                  <Divider>Validations</Divider>
                  <DisplayItemStatus
                    item={itemQuery.data}
                    action={action}
                    handleSelectedUpdate={handleSelectedUpdate}
                  />
                  <Divider>Relations</Divider>
                  <ItemLinkage
                    item={itemQuery.data}
                    action={action}
                    handleItemOpen={handleChangeItem}
                    setItem={setItem}
                  />

                  {isImageItem(itemQuery.data) && (
                    <React.Fragment>
                      <Divider>Thumbnail</Divider>
                      <Thumbnail
                        image={itemQuery.data}
                        openImage={handleOpenImageChange}
                        size={{ width: 512, height: 512 }}
                      />
                    </React.Fragment>
                  )}
                  {Object.keys(itemQuery.data.attributes).length > 0 && (
                    <Divider>Attributes</Divider>
                  )}
                  <AttributeDetails
                    schemas={itemSchema.attributes}
                    attributes={itemQuery.data.attributes}
                    action={action}
                    handleAttributeOpen={handleAttributeOpen}
                    handleAttributeUpdate={baseHandleAttributeUpdate}
                  />
                </Stack>
              )}
              {openedAttributes.length > 0 && (
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  action={action}
                  handleNestedAttributeChange={handleNestedAttributeChange}
                  handleAttributeOpen={handleAttributeOpen}
                  handleAttributeUpdate={baseHandleAttributeUpdate}
                />
              )}
            </Grid>
            {(privateOpen || previewOpen) && (
              <Grid size={{ xs: 6 }}>
                {previewOpen && (
                  <Stack spacing={1}>
                    <Divider>
                      <Typography variant="h6">Preview</Typography>
                    </Divider>

                    <DisplayPreview
                      showPreview={previewOpen}
                      itemUid={itemQuery.data.uid}
                    />
                  </Stack>
                )}
                {privateOpen && (
                  <Stack spacing={1}>
                    <Divider>
                      <Typography variant="h6">Private</Typography>
                    </Divider>
                    <Box sx={{ maxHeight: '70vh', overflow: 'auto' }}>
                      <AttributeDetails
                        schemas={itemSchema.privateAttributes}
                        attributes={itemQuery.data.privateAttributes}
                        action={action}
                        handleAttributeOpen={handleAttributeOpen}
                        handleAttributeUpdate={baseHandleAttributeUpdate}
                        spacing={2}
                      />
                    </Box>
                  </Stack>
                )}
              </Grid>
            )}
          </Grid>
        </CardContent>
        <CardActions>
          {action === ItemDetailAction.VIEW && (
            <Button
              onClick={() => {
                changeAction(ItemDetailAction.EDIT)
              }}
            >
              Edit
            </Button>
          )}
          {(action === ItemDetailAction.EDIT || action === ItemDetailAction.COPY) && (
            <React.Fragment>
              <Button
                onClick={() => {
                  changeAction(ItemDetailAction.VIEW)
                }}
              >
                Cancel
              </Button>

              <Button onClick={handleSave}>Save</Button>
            </React.Fragment>
          )}
          <Button onClick={() => setOpen(false)}>Close</Button>
          <span style={{ flex: 1 }} />
          <Button
            onClick={() => {
              setPreviewOpen(false)
              setPrivateOpen(!privateOpen)
            }}
            disabled={Object.keys(itemQuery.data.privateAttributes).length === 0}
          >
            <Security />
          </Button>
          <Button
            onClick={() => {
              setPrivateOpen(false)
              setPreviewOpen(!previewOpen)
            }}
          >
            <Preview />
          </Button>
          <Button
            onClick={() =>
              window.open(
                `/project/${projectUid}/images_for_item/${itemUid}`,
                '_blank',
                'noopener,noreferrer,width=1024,height=1024,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes',
              )
            }
          >
            <PhotoLibrary />
          </Button>
          {!windowed && (
            <Button
              onClick={() => {
                window.open(
                  `/project/${projectUid}}/item/${itemUid}`,
                  '_blank',
                  'noopener,noreferrer,width=600,height=800,menubar=no,toolbar=no,location=no,status=no,scrollbars=yes,resizable=yes',
                )
                setOpen(false)
              }}
            >
              <OpenInNew />
            </Button>
          )}
        </CardActions>
      </Card>

      {openedImage !== undefined && (
        <ValidateImage open={imageOpen} image={openedImage} setOpen={setImageOpen} />
      )}
    </Spinner>
  )
}
