import type { Item } from 'models/items'
import React, { useEffect, useState, type ReactElement } from 'react'
import itemApi from 'services/api/item_api'
import {
  Button,
  Card,
  CardContent,
  CardActions,
  CardHeader,
  Stack,
} from '@mui/material'
import Spinner from 'components/spinner'
import type { Attribute } from 'models/attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import AttributeDetails from '../attribute/attribute_details'
import ItemLinkage from './item_linkage'
import NestedAttributeDetails from '../attribute/nested_attribute_details'
import { Action } from 'models/table_item'

interface ItemDetailsProps {
  itemUid: string | undefined
  action: Action
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function ItemDetails({
  itemUid,
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

  const getItem = (itemUid: string): void => {
    itemApi
      .get(itemUid)
      .then((responseItem) => {
        setOpenedAttributes([])
        setItem(responseItem)
        setIsLoading(false)
      })
      .catch((x) => {
        console.error('Failed to get items', x)
      })
  }

  useEffect(() => {
    if (currentItemUid === undefined) {
      return
    }
    getItem(currentItemUid)
  }, [currentItemUid])

  useEffect(() => {
    if (itemUid === undefined) {
      return
    }
    setCurrentItemUid(itemUid)
  }, [itemUid])

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
    // TODO handle save
  }

  let handleAttributeUpdate: ((attribute: Attribute<any, any>) => void) | undefined
  if (currentAction === Action.EDIT) {
    handleAttributeUpdate = (attribute: Attribute<any, any>): void => {
      const updatedItem = { ...item }
      updatedItem.attributes[attribute.schema.tag] = attribute
      console.log('updated item', updatedItem.attributes)
      setItem(updatedItem)
    }
  }
  return (
    <Spinner loading={isLoading}>
      <Card>
        <CardHeader title={item.schema.displayName + ': ' + item.name} />
        <CardContent>
          <Grid container spacing={2}>
            <Grid xs={12}>
              {openedAttributes.length === 0 && (
                <Stack spacing={2}>
                  <FormControlLabel
                    label="Selected"
                    control={<Checkbox value={item.selected} />}
                  />
                  <ItemLinkage item={item} handleItemOpen={handleItemOpen} />
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
          {currentAction === Action.EDIT && (
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
    </Spinner>
  )
}
