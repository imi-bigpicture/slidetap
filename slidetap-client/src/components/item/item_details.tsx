import type { Item } from 'models/items'
import React, { useEffect, useState, type ReactElement } from 'react'
import itemApi from 'services/api/item_api'
import {
  Button,
  Card,
  CardContent,
  CardActions,
  CardHeader,
  TextField,
  Stack,
} from '@mui/material'
import Spinner from 'components/spinner'
import type { Attribute } from 'models/attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import AttributeDetails from './attribute_details'
import ItemLinkage from './item_linkage'
import NestedAttributeDetails from './nested_attribute_details'

interface ItemDetailsProps {
  itemUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function ItemDetails({
  itemUid,
  setOpen,
}: ItemDetailsProps): ReactElement {
  const [currentItemUid, setCurrentItemUid] = useState<string | undefined>(itemUid)
  const [item, setItem] = useState<Item>()
  const [openedAttributes, setOpenedAttributes] = useState<Array<Attribute<any, any>>>(
    [],
  )
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const getItem = (itemUid: string): void => {
    itemApi
      .get(itemUid)
      .then((responseItem) => {
        console.log('got item', responseItem)
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
    console.log('handling opening child object attribute', attribute)
    setOpenedAttributes([...openedAttributes, attribute])
  }

  const handleItemOpen = (itemUid: string): void => {
    setCurrentItemUid(itemUid)
  }

  const handleClose = (): void => {
    setOpen(false)
  }
  const handleSave = (): void => {}

  return (
    <Spinner loading={isLoading}>
      <Card>
        <CardHeader title={item.schema.displayName + ': ' + item.name}>
          <Grid>
            <TextField label="type" value={item.schema.displayName} />
            <TextField label="name" value={item.name} />
          </Grid>
        </CardHeader>
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
                    />
                  )}
                </Stack>
              )}
              {openedAttributes.length > 0 && (
                <NestedAttributeDetails
                  item={item}
                  openedAttributes={openedAttributes}
                  setOpenedAttributes={setOpenedAttributes}
                  handleAttributeOpen={handleAttributeOpen}
                />
              )}
            </Grid>
          </Grid>
        </CardContent>
        <CardActions disableSpacing>
          <Button onClick={handleSave}>Save</Button>
          <Button onClick={handleClose}>Close</Button>
        </CardActions>
      </Card>
    </Spinner>
  )
}
