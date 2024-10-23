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
  LinearProgress,
  Stack,
  TextField,
} from '@mui/material'
import Grid from '@mui/material/Grid2'
import { useQuery } from '@tanstack/react-query'
import Spinner from 'components/spinner'
import { isImageSchema, isObservationSchema, isSampleSchema } from 'models/helpers'
import { ItemValueTypeStrings } from 'models/schema'
import React, { type ReactElement } from 'react'
import schemaApi from 'services/api/schema_api'

interface DisplayItemSchemaDetailsProps {
  schemaUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function DisplayItemSchemaDetails({
  schemaUid,
  setOpen,
}: DisplayItemSchemaDetailsProps): ReactElement {
  const schemaQuery = useQuery({
    queryKey: ['schema', schemaUid],
    queryFn: async () => {
      if (schemaUid === undefined) {
        return undefined
      }
      return await schemaApi.getItemSchema(schemaUid)
    },
  })

  if (schemaQuery.data === undefined) {
    return <LinearProgress />
  }

  const handleClose = (): void => {
    setOpen(false)
  }

  return (
    <Spinner loading={schemaQuery.isLoading}>
      <Card style={{ maxHeight: '80vh', overflowY: 'auto' }}>
        <CardHeader title={schemaQuery.data.displayName} />
        <CardContent>
          <Grid container spacing={1}>
            <Grid size={{ xs: 12 }}>
              <Stack direction="column" spacing={2}>
                <FormControl>
                  <FormLabel component="legend">Schema type</FormLabel>
                  <TextField
                    value={ItemValueTypeStrings[schemaQuery.data.itemValueType]}
                    size="small"
                    InputProps={{ readOnly: true }}
                  />
                </FormControl>
                {isSampleSchema(schemaQuery.data) && (
                  <>
                    <FormControl>
                      <FormLabel component="legend">Parents</FormLabel>
                      <TextField
                        value={schemaQuery.data.parents.map(
                          (parent) => parent.parent.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Children</FormLabel>
                      <TextField
                        value={schemaQuery.data.children.map(
                          (child) => child.child.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Images</FormLabel>
                      <TextField
                        value={schemaQuery.data.images.map(
                          (image) => image.image.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Observations</FormLabel>
                      <TextField
                        value={schemaQuery.data.observations.map(
                          (observation) => observation.observation.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                  </>
                )}
                {isImageSchema(schemaQuery.data) && (
                  <>
                    <FormControl>
                      <FormLabel component="legend">Sample</FormLabel>
                      <TextField
                        value={schemaQuery.data.samples.map(
                          (sample) => sample.sample.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Observation</FormLabel>
                      <TextField
                        value={schemaQuery.data.observations.map(
                          (observation) => observation.observation.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                  </>
                )}
                {isObservationSchema(schemaQuery.data) && (
                  <>
                    <FormControl>
                      <FormLabel component="legend">Sample</FormLabel>
                      <TextField
                        value={schemaQuery.data.samples.map(
                          (sample) => sample.sample.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                    <FormControl>
                      <FormLabel component="legend">Image</FormLabel>
                      <TextField
                        value={schemaQuery.data.images.map(
                          (image) => image.image.displayName,
                        )}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </FormControl>
                  </>
                )}
                <FormControl>
                  <FormLabel component="legend">Attributes</FormLabel>
                  <Stack spacing={1}>
                    {schemaQuery.data.attributes.map((attribute) => (
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
