import type { Item } from 'models/items'
import React, { useEffect, useState, type ReactElement } from 'react'
import itemApi from 'services/api/item_api'
import {
  Button,
  Breadcrumbs,
  Card,
  CardContent,
  CardActions,
  Link,
  TextField,
  Stack,
  CardHeader,
} from '@mui/material'
import Spinner from 'components/spinner'
import type { Attribute } from 'models/attribute'
import DisplayAttribute from 'components/attribute/display_attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import Checkbox from '@mui/material/Checkbox'
import FormControlLabel from '@mui/material/FormControlLabel'
import HomeIcon from '@mui/icons-material/Home'
import { isImageItem, isObservationItem, isSampleItem } from 'models/helpers'
import DisplayItemReferences from './display_item_references'

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
  const handleBreadcrumbChange = (uid: string): void => {
    if (uid === item.uid) {
      setOpenedAttributes([])
      return
    }
    const parentAttributeIndex = openedAttributes.findIndex(
      (attribute) => attribute.uid === uid,
    )
    if (parentAttributeIndex >= 0) {
      setOpenedAttributes(openedAttributes.slice(0, parentAttributeIndex + 1))
    }
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
        <CardContent>
          <Breadcrumbs aria-label="breadcrumb">
            <Link
              onClick={() => {
                handleBreadcrumbChange(item.uid)
              }}
            >
              <HomeIcon />
            </Link>
            {openedAttributes.map((attribute) => {
              return (
                <Link
                  key={attribute.uid}
                  onClick={() => {
                    handleBreadcrumbChange(attribute.uid)
                  }}
                >
                  {attribute.schema.displayName}
                </Link>
              )
            })}
          </Breadcrumbs>
          <Grid container spacing={2}>
            <Grid>
              {openedAttributes.length === 0 && (
                <Stack spacing={2}>
                  <Stack spacing={1} direction="row" sx={{ margin: 2 }}>
                    <TextField label="type" value={item.schema.displayName} />
                    <TextField label="name" value={item.name} />
                  </Stack>
                  <FormControlLabel
                    label="Selected"
                    control={<Checkbox value={item.selected} />}
                  />
                  {isSampleItem(item) && (
                    <React.Fragment>
                      <DisplayItemReferences
                        title="Parents"
                        references={item.parents}
                        handleItemOpen={handleItemOpen}
                      />
                      <DisplayItemReferences
                        title="Children"
                        references={item.children}
                        handleItemOpen={handleItemOpen}
                      />
                    </React.Fragment>
                  )}
                  {isImageItem(item) && (
                    <React.Fragment>
                      <TextField label="Status" value={item.status} />
                      <DisplayItemReferences
                        title="Samples"
                        references={item.samples}
                        handleItemOpen={handleItemOpen}
                      />
                    </React.Fragment>
                  )}
                  {isObservationItem(item) && (
                    <React.Fragment>
                      <DisplayItemReferences
                        title="Observed on"
                        references={[item.observedOn]}
                        handleItemOpen={handleItemOpen}
                      />
                    </React.Fragment>
                  )}
                  <Card>
                    <CardHeader title="Attributes" />
                    <CardContent>
                      {Object.values(item.attributes).map((attribute) => {
                        return (
                          <Grid key={attribute.uid}>
                            <DisplayAttribute
                              key={attribute.uid}
                              attribute={attribute}
                              hideLabel={false}
                              handleAttributeOpen={handleAttributeOpen}
                              complexAttributeAsButton={true}
                            />
                          </Grid>
                        )
                      })}
                    </CardContent>
                  </Card>
                </Stack>
              )}
              {openedAttributes.length > 0 && (
                <DisplayAttribute
                  attribute={openedAttributes.slice(-1)[0]}
                  hideLabel={false}
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
