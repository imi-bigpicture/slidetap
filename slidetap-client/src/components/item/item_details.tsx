import type { Image, Item, ItemReference } from 'models/items'
import React, { useEffect, useState, type ReactElement } from 'react'
import itemApi from 'services/api/item_api'
import {
  Button,
  Card,
  CardContent,
  CardActions,
  CardHeader,
  Stack,
  Radio,
  Checkbox,
  FormControlLabel,
  FormControl,
  TextField,
  FormLabel,
} from '@mui/material'
import Spinner from 'components/spinner'
import type { Attribute } from 'models/attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import AttributeDetails from '../attribute/attribute_details'
import ItemLinkage from './item_linkage'
import NestedAttributeDetails from '../attribute/nested_attribute_details'
import { Action, ActionStrings } from 'models/table_item'
import Thumbnail from 'components/project/validate/thumbnail'
import { isImageItem } from 'models/helpers'
import { ValidateImage } from 'components/project/validate/validate_image'

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
  const [openedAttributes, setOpenedAttributes] = useState<Array<Attribute<any, any>>>(
    [],
  )
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [currentAction, setCurrentAction] = useState<Action>(action)
  const [imageOpen, setImageOpen] = useState(false)
  const [openedImage, setOpenedImage] = useState<Image>()

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
          setOpenedAttributes([])
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
    console.log('action', action)
    setCurrentAction(action)
  }, [action])

  if (item === undefined) {
    return <></>
  }

  const handleAttributeOpen = (attribute: Attribute<any, any>): void => {
    setOpenedAttributes([...openedAttributes, attribute])
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
      console.log('save item', item)
      savedItem = itemApi.save(item)
    }
    savedItem
      .catch((x) => {
        console.error('Failed to update item', x)
      })
      .then(() => {
        setCurrentItemUid(item.uid)
        setCurrentAction(Action.VIEW)
      })
      .catch((x) => {
        console.error('Failed to get item', x)
      })
  }

  let handleAttributeUpdate: ((attribute: Attribute<any, any>) => void) | undefined
  if (currentAction !== Action.VIEW) {
    handleAttributeUpdate = (attribute: Attribute<any, any>): void => {
      const updatedItem = { ...item }
      updatedItem.attributes[attribute.schema.tag] = attribute
      setItem(updatedItem)
    }
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
          <Grid container spacing={2}>
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
              {openedAttributes.length === 0 && (
                <Stack spacing={2}>
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
                      handleAttributeOpen={handleAttributeOpen}
                      handleAttributeUpdate={handleAttributeUpdate}
                    />
                  )}
                </Stack>
              )}
              {openedAttributes.length > 0 && (
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  setOpenedAttributes={setOpenedAttributes}
                  handleAttributeOpen={handleAttributeOpen}
                  handleAttributeUpdate={handleAttributeUpdate}
                />
              )}
            </Grid>
          </Grid>
        </CardContent>
        <CardActions disableSpacing>
          {currentAction === Action.VIEW && (
            <Button
              onClick={() => {
                setCurrentAction(Action.EDIT)
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
                  setCurrentAction(Action.VIEW)
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
