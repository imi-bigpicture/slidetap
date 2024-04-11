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
  FormControl,
  FormLabel,
  Stack,
  TextField,
} from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import Spinner from 'components/spinner'
import { isImageSchema, isObservationSchema, isSampleSchema } from 'models/helpers'
import { ItemValueTypeStrings, type ItemSchema } from 'models/schema'
import React, { useEffect, useState, type ReactElement } from 'react'
import schemaApi from 'services/api/schema_api'

interface DisplayItemSchemaDetailsProps {
  schemaUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function DisplayItemSchemaDetails({
  schemaUid,
  setOpen,
}: DisplayItemSchemaDetailsProps): ReactElement {
  const [currentSchemaUid, setCurrentSchemaUid] = useState<string | undefined>(
    schemaUid,
  )
  const [schema, setSchema] = useState<ItemSchema>()
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    const getSchema = (schemaUid: string): void => {
      schemaApi
        .getItemSchema(schemaUid)
        .then((responseItem) => {
          setSchema(responseItem)
          setIsLoading(false)
        })
        .catch((x) => {
          console.error('Failed to get items', x)
        })
    }
    if (currentSchemaUid === undefined) {
      return
    }
    getSchema(currentSchemaUid)
  }, [currentSchemaUid])

  useEffect(() => {
    if (schemaUid === undefined) {
      return
    }
    setCurrentSchemaUid(schemaUid)
  }, [schemaUid])

  if (schema === undefined) {
    return <></>
  }

  const handleClose = (): void => {
    setOpen(false)
  }

  return (
    <Spinner loading={isLoading}>
      <Card style={{ maxHeight: '80vh', overflowY: 'auto' }}>
        <CardHeader title={schema.displayName} />
        <CardContent>
          <Grid container spacing={1}>
            <Grid xs={12}>
              <Stack direction="column" spacing={2}>
                <FormControl>
                  <FormLabel component="legend">Schema type</FormLabel>
                  <TextField
                    value={ItemValueTypeStrings[schema.itemValueType]}
                    size="small"
                    InputProps={{ readOnly: true }}
                  />
                </FormControl>
                {isSampleSchema(schema) && (
                  <>
                    <FormControl>
                      <FormLabel component="legend">Parents</FormLabel>
                      <TextField
                        value={schema.parents.map(
                          (parent) => parent.parent.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Children</FormLabel>
                      <TextField
                        value={schema.children.map((child) => child.child.displayName)}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Images</FormLabel>
                      <TextField
                        value={schema.images.map((image) => image.image.displayName)}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Observations</FormLabel>
                      <TextField
                        value={schema.observations.map(
                          (observation) => observation.observation.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                  </>
                )}
                {isImageSchema(schema) && (
                  <>
                    <FormControl>
                      <FormLabel component="legend">Sample</FormLabel>
                      <TextField
                        value={schema.samples.map(
                          (sample) => sample.sample.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Observation</FormLabel>
                      <TextField
                        value={schema.observations.map(
                          (observation) => observation.observation.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                  </>
                )}
                {isObservationSchema(schema) && (
                  <>
                    <FormControl>
                      <FormLabel component="legend">Sample</FormLabel>
                      <TextField
                        value={schema.samples.map(
                          (sample) => sample.sample.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Image</FormLabel>
                      <TextField
                        value={schema.images.map((image) => image.image.displayName)}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                  </>
                )}
                <FormControl>
                  <FormLabel component="legend">Attributes</FormLabel>
                  <Stack spacing={1}>
                    {schema.attributes.map((attribute) => (
                      <TextField
                        key={attribute.uid}
                        value={attribute.displayName}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    ))}
                  </Stack>
                </FormControl>
              </Stack>
            </Grid>
          </Grid>
        </CardContent>
        <CardActions disableSpacing>
          <Button onClick={handleClose}>Close</Button>
        </CardActions>
      </Card>
    </Spinner>
  )
}
