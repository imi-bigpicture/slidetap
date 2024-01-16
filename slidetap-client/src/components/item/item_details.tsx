import {
  Button,
  Card,
  CardActions,
  CardContent,
  CardHeader,
  Checkbox,
  FormControl,
  FormControlLabel,
  FormLabel,
  Radio,
  Stack,
  TextField,
} from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import Thumbnail from 'components/project/validate/thumbnail'
import { ValidateImage } from 'components/project/validate/validate_image'
import Spinner from 'components/spinner'
import type { Attribute } from 'models/attribute'
import { isImageItem } from 'models/helpers'
import type { Image, Item } from 'models/items'
import { Action, ActionStrings } from 'models/table_item'
import React, { useEffect, useState, type ReactElement } from 'react'
import itemApi from 'services/api/item_api'
import AttributeDetails from '../attribute/attribute_details'
import NestedAttributeDetails from '../attribute/nested_attribute_details'
import DisplayPreview from './display_preview'
import ItemLinkage from './item_linkage'

interface ItemDetailsProps {
  itemUid: string | undefined
  itemSchemaUid: string | undefined
  projectUid: string
  action: Action.VIEW | Action.EDIT | Action.NEW | Action.COPY
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function ItemDetails({
  itemUid,
  itemSchemaUid,
  projectUid,
  action,
  setOpen,
}: ItemDetailsProps): ReactElement {
  const [currentItemUid, setCurrentItemUid] = useState<string | undefined>(itemUid)
  const [item, setItem] = useState<Item>()
  const [openedAttributes, setOpenedAttributes] = useState<
    Array<{
      attribute: Attribute<any, any>
      updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>
    }>
  >([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [currentAction, setCurrentAction] = useState<Action>(action)
  const [imageOpen, setImageOpen] = useState(false)
  const [openedImage, setOpenedImage] = useState<Image>()
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => {
    const getItem = (itemUid: string, action: Action): void => {
      let fetchedItem: Promise<Item>
      if (action === Action.NEW && itemSchemaUid !== undefined) {
        fetchedItem = itemApi.create(itemSchemaUid, projectUid)
      } else if (action === Action.COPY) {
        fetchedItem = itemApi.copy(itemUid)
      } else {
        fetchedItem = itemApi.get(itemUid)
      }

      fetchedItem
        .then((responseItem) => {
          console.log('Got item', responseItem.uid, currentItemUid)
          // setOpenedAttributes([])
          setItem(responseItem)
          setIsLoading(false)
        })
        .catch((x) => {
          console.error('Failed to get items', x)
        })
    }
    if (currentItemUid === undefined) {
      return
    }
    getItem(currentItemUid, currentAction)
  }, [currentItemUid, currentAction, itemSchemaUid, projectUid])

  useEffect(() => {
    if (itemUid === undefined) {
      return
    }
    setCurrentItemUid(itemUid)
  }, [itemUid])

  useEffect(() => {
    setCurrentAction(action)
  }, [action])

  if (item === undefined) {
    return <></>
  }

  const changeAction = (action: Action): void => {
    const openedAttributesToRestore = openedAttributes
    console.log('change action', action, openedAttributesToRestore)

    setCurrentAction(action)
    setOpenedAttributes(openedAttributesToRestore)
  }

  const handleAttributeOpen = (
    attribute: Attribute<any, any>,
    updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>,
  ): void => {
    setOpenedAttributes([...openedAttributes, { attribute, updateAttribute }])
  }

  const handleItemOpen = (itemUid: string): void => {
    setCurrentItemUid(itemUid)
  }

  const handleClose = (): void => {
    setOpen(false)
  }
  const handleSave = (): void => {
    if (currentItemUid === undefined) {
      return
    }
    let savedItem: Promise<Item>
    if (action === Action.NEW || action === Action.COPY) {
      savedItem = itemApi.add(item, projectUid)
    } else {
      savedItem = itemApi.save(item)
    }
    savedItem
      .catch((x) => {
        console.error('Failed to update item', x)
      })
      .then((newItem) => {
        if (newItem === undefined) {
          return
        }
        setCurrentItemUid(newItem.uid)
        changeAction(Action.VIEW)
      })
      .catch((x) => {
        console.error('Failed to get item', x)
      })
  }

  const handleShowPreivew = (): void => {
    setShowPreview(!showPreview)
  }

  const baseHandleAttributeUpdate = (attribute: Attribute<any, any>): void => {
    const updatedItem = { ...item }
    updatedItem.attributes[attribute.schema.tag] = attribute
    setItem(updatedItem)
  }

  const handleSelectedUpdate = (selected: boolean): void => {
    const updatedItem = { ...item }
    updatedItem.selected = selected
    setItem(updatedItem)
  }

  const handleNameUpdate = (name: string): void => {
    const updatedItem = { ...item }
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
  return (
    <Spinner loading={isLoading}>
      <Card style={{ maxHeight: '80vh', overflowY: 'auto' }}>
        <CardHeader
          title={
            ActionStrings[currentAction] +
            ' ' +
            item.schema.displayName +
            ': ' +
            item.name
          }
        />
        <CardContent>
          <Grid container spacing={1}>
            <Grid xs={12}>
              <FormControl component="fieldset" variant="standard">
                <FormLabel>Identifier</FormLabel>
                <TextField
                  value={item.name}
                  onChange={(event) => {
                    handleNameUpdate(event.target.value)
                  }}
                  InputProps={{ readOnly: currentAction === Action.VIEW }}
                />
              </FormControl>
              {showPreview && <DisplayPreview itemUid={item.uid} />}
              {!showPreview && openedAttributes.length === 0 && (
                <Stack spacing={1}>
                  <FormControlLabel
                    label="Selected"
                    control={
                      currentAction === Action.VIEW ? (
                        <Radio readOnly={true} />
                      ) : (
                        <Checkbox />
                      )
                    }
                    checked={item.selected}
                    onChange={(event, value) => {
                      if (currentAction === Action.VIEW) {
                        return
                      }
                      handleSelectedUpdate(value)
                    }}
                  />
                  <ItemLinkage
                    item={item}
                    action={currentAction}
                    handleItemOpen={handleItemOpen}
                    setItem={setItem}
                  />
                  {isImageItem(item) && (
                    <Thumbnail
                      image={item}
                      openImage={handleOpenImageChange}
                      size={{ width: 512, height: 512 }}
                    />
                  )}
                  {Object.keys(item.attributes).length > 0 && (
                    <AttributeDetails
                      attributes={item.attributes}
                      action={currentAction}
                      handleAttributeOpen={handleAttributeOpen}
                      handleAttributeUpdate={baseHandleAttributeUpdate}
                    />
                  )}
                </Stack>
              )}
              {!showPreview && openedAttributes.length > 0 && (
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  action={currentAction}
                  handleNestedAttributeChange={handleNestedAttributeChange}
                  handleAttributeOpen={handleAttributeOpen}
                  handleAttributeUpdate={baseHandleAttributeUpdate}
                />
              )}
            </Grid>
          </Grid>
        </CardContent>
        <CardActions disableSpacing>
          {currentAction === Action.VIEW && (
            <Button
              onClick={() => {
                changeAction(Action.EDIT)
              }}
            >
              Edit
            </Button>
          )}
          {(currentAction === Action.EDIT ||
            currentAction === Action.COPY ||
            currentAction === Action.NEW) && (
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
          <Button onClick={handleShowPreivew}>Preview</Button>
          <Button onClick={handleClose}>Close</Button>
        </CardActions>
      </Card>

      {openedImage !== undefined && (
        <ValidateImage open={imageOpen} image={openedImage} setOpen={setImageOpen} />
      )}
    </Spinner>
  )
}
