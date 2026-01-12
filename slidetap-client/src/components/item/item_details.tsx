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
  Chip,
  Divider,
  LinearProgress,
  Link,
  Stack,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid'

import { OpenInNew, PhotoLibrary, Preview, Security } from '@mui/icons-material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useEffect, useState, type ReactElement } from 'react'
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
import tagApi from 'src/services/api/tag_api'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import AttributeDetails from '../attribute/attribute_details'
import NestedAttributeDetails from '../attribute/nested_attribute_details'
import DisplayItemTags from './display_item_tags'
import DisplayPreview from './display_preview'
import DisplayItemIdentifiers from './item_identifiers'
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
  const [newTagsToSave, setNewTagsToSave] = useState<string[]>([])
  const [item, setItem] = useState<Item>()

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
  useEffect(() => {
    if (itemQuery.data !== undefined) {
      setItem(itemQuery.data)
    }
  }, [itemQuery.data])

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
    const savedTags = await Promise.all(
      newTagsToSave.map(
        async (tag) =>
          await tagApi.save({
            uid: '00000000-0000-0000-0000-000000000000',
            name: tag,
            description: null,
            color: null,
          }),
      ),
    ).then((tags) => tags.map((tag) => tag.uid))
    item.tags = [...item.tags, ...savedTags]
    if (action === ItemDetailAction.COPY) {
      return await itemApi.add(item)
    }

    return await itemApi.save(item)
  }

  const saveMutation = useMutation({
    mutationFn: save,
    onSuccess: (data) => {
      // Update the item in the query cache
      queryClient.setQueryData(['item', data.uid, ItemDetailAction.VIEW], data)
      // Also update the item in any item lists
      queryClient.setQueriesData(
        { queryKey: ['items', data.schemaUid], exact: false },
        (oldData: { items: Item[]; count: number }) => {
          return {
            items: oldData.items.map((item: Item) =>
              item.uid === data.uid ? data : item,
            ),
            count: oldData.count,
          }
        },
      )
      changeAction(ItemDetailAction.VIEW)
    },
  })

  if (item === undefined || itemQuery.data === undefined) {
    if (itemQuery.isLoading) {
      return <LinearProgress />
    } else {
      return <></>
    }
  }

  const handleSave = (): void => {
    saveMutation.mutate({ item, action })
  }

  const handleAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    const updatedAttributes = { ...item.attributes }
    updatedAttributes[tag] = attribute
    const updatedItem = { ...item, attributes: updatedAttributes }
    setItem(updatedItem)
  }

  const handlePrivateAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    const updatedAttributes = { ...item.privateAttributes }
    updatedAttributes[tag] = attribute
    const updatedItem = { ...item, privateAttributes: updatedAttributes }
    setItem(updatedItem)
  }

  const handleIdentifierUpdate = (identifier: string): void => {
    const updatedItem = { ...item }
    updatedItem.identifier = identifier
    setItem(updatedItem)
  }

  const handleNameUpdate = (name: string): void => {
    const updatedItem = { ...item }
    updatedItem.name = name
    setItem(updatedItem)
  }

  const handleCommentUpdate = (comment: string): void => {
    const updatedItem = { ...item }
    updatedItem.comment = comment
    setItem(updatedItem)
  }

  const handleTagsUpdate = (tags: string[]): void => {
    const updatedItem = { ...item, tags }
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

  const itemSchema = (function () {
    switch (item.itemValueType) {
      case ItemValueType.SAMPLE:
        return rootSchema.samples[item.schemaUid]
      case ItemValueType.IMAGE:
        return rootSchema.images[item.schemaUid]
      case ItemValueType.OBSERVATION:
        return rootSchema.observations[item.schemaUid]
      case ItemValueType.ANNOTATION:
        return rootSchema.annotations[item.schemaUid]
      default:
        throw new Error('Unknown item value type')
    }
  })()

  const nestedAttributesOpened = openedAttributes.length > 0

  return (
    <Spinner loading={itemQuery.isLoading}>
      <Card>
        <CardContent>
          <Grid container>
            <Grid size="grow">
              {!nestedAttributesOpened ? (
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
                  <DisplayItemIdentifiers
                    item={item}
                    action={action}
                    direction="row"
                    handleIdentifierUpdate={handleIdentifierUpdate}
                    handleNameUpdate={handleNameUpdate}
                    handleCommentUpdate={handleCommentUpdate}
                  />

                  <DisplayItemTags
                    tagUids={item.tags}
                    newTagNames={newTagsToSave}
                    editable={action !== ItemDetailAction.VIEW}
                    handleTagsUpdate={handleTagsUpdate}
                    setNewTags={setNewTagsToSave}
                  />

                  <Divider>
                    <Chip
                      label="Relations"
                      color={item.validRelations ? 'default' : 'error'}
                      size="small"
                      variant="outlined"
                    />
                  </Divider>
                  <ItemLinkage
                    item={item}
                    action={action}
                    handleItemOpen={handleChangeItem}
                    setItem={setItem}
                  />

                  {isImageItem(item) && (
                    <React.Fragment>
                      <Divider>Thumbnail</Divider>
                      <Thumbnail
                        image={item}
                        openImage={handleOpenImageChange}
                        size={{ width: 512, height: 512 }}
                      />
                    </React.Fragment>
                  )}
                  {Object.keys(item.attributes).length > 0 && (
                    <Divider>
                      <Chip
                        label="Attributes"
                        color={item.validAttributes ? 'default' : 'error'}
                        size="small"
                        variant="outlined"
                      />
                    </Divider>
                  )}
                  <AttributeDetails
                    schemas={itemSchema.attributes}
                    attributes={item.attributes}
                    action={action}
                    handleAttributeOpen={handleAttributeOpen}
                    handleAttributeUpdate={handleAttributeUpdate}
                  />
                </Stack>
              ) : (
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  action={action}
                  handleNestedAttributeChange={handleNestedAttributeChange}
                  handleAttributeOpen={handleAttributeOpen}
                  handleAttributeUpdate={handleAttributeUpdate}
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

                    <DisplayPreview showPreview={previewOpen} itemUid={item.uid} />
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
                        attributes={item.privateAttributes}
                        action={action}
                        handleAttributeOpen={handleAttributeOpen}
                        handleAttributeUpdate={handlePrivateAttributeUpdate}
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
                  setItem(itemQuery.data!)
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
            disabled={Object.keys(item.privateAttributes).length === 0}
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
