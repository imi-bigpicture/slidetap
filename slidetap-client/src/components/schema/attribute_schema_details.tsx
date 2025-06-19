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
  FormControlLabel,
  FormLabel,
  LinearProgress,
  Radio,
  Stack,
  TextField,
} from '@mui/material'
import Grid from '@mui/material/Grid'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import Spinner from 'src/components/spinner'
import { AttributeValueTypeStrings } from 'src/models/attribute_value_type'
import { DatetimeTypeStrings } from 'src/models/datetime_type'
import {
  isCodeAttributeSchema,
  isDatetimeAttributeSchema,
  isEnumAttributeSchema,
  isListAttributeSchema,
  isMeasurementAttributeSchema,
  isNumericAttributeSchema,
  isObjectAttributeSchema,
  isUnionAttributeSchema,
} from 'src/models/helpers'
import schemaApi from 'src/services/api/schema_api'

interface DisplayAttributeSchemaDetailsProps {
  schemaUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function DisplayAttributeSchemaDetails({
  schemaUid,
  setOpen,
}: DisplayAttributeSchemaDetailsProps): ReactElement {
  const schemaQuery = useQuery({
    queryKey: ['schema', schemaUid],
    queryFn: async () => {
      if (schemaUid === undefined) {
        return undefined
      }
      return await schemaApi.getAttributeSchema(schemaUid)
    },
    enabled: schemaUid !== undefined,
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
              <Stack direction="column" spacing={1}>
                <FormControl>
                  <FormLabel component="legend">Schema type</FormLabel>
                  <TextField
                    value={
                      AttributeValueTypeStrings[schemaQuery.data.attributeValueType]
                    }
                    size="small"
                    InputProps={{ readOnly: true }}
                  />
                </FormControl>
                <Stack spacing={1} direction="row" justifyContent="space-evenly">
                  <FormControlLabel
                    label="Optional"
                    control={<Radio readOnly={true} />}
                    checked={schemaQuery.data.optional}
                  />
                  <FormControlLabel
                    label="Read only"
                    control={<Radio readOnly={true} />}
                    checked={schemaQuery.data.readOnly}
                  />
                </Stack>
                {isEnumAttributeSchema(schemaQuery.data) && (
                  <FormControl>
                    <FormLabel component="legend">Allowed values</FormLabel>
                    <TextField
                      value={schemaQuery.data.allowedValues}
                      size="small"
                      InputProps={{ readOnly: true }}
                    />
                  </FormControl>
                )}
                {isDatetimeAttributeSchema(schemaQuery.data) && (
                  <FormControl>
                    <FormLabel component="legend">Datetime type</FormLabel>
                    <TextField
                      value={DatetimeTypeStrings[schemaQuery.data.datetimeType]}
                      size="small"
                      InputProps={{ readOnly: true }}
                    />
                  </FormControl>
                )}
                {isNumericAttributeSchema(schemaQuery.data) && (
                  <FormControlLabel
                    label="Is integer"
                    control={<Radio readOnly={true} />}
                    checked={schemaQuery.data.isInt}
                  />
                )}
                {isMeasurementAttributeSchema(schemaQuery.data) && (
                  <FormControl>
                    <FormLabel component="legend">Allowed units</FormLabel>
                    <TextField
                      value={schemaQuery.data.allowedUnits}
                      size="small"
                      InputProps={{ readOnly: true }}
                    />
                  </FormControl>
                )}
                {isCodeAttributeSchema(schemaQuery.data) && (
                  <FormControl>
                    <FormLabel component="legend">Allowed schemas</FormLabel>
                    <TextField
                      value={schemaQuery.data.allowedSchemas ?? ''}
                      size="small"
                      InputProps={{ readOnly: true }}
                    />
                  </FormControl>
                )}
                {isObjectAttributeSchema(schemaQuery.data) && (
                  <FormControl>
                    <FormLabel component="legend">Attributes</FormLabel>
                    <Stack spacing={1}>
                      {Object.values(schemaQuery.data.attributes).map((attribute) => (
                        <TextField
                          key={attribute.uid}
                          value={attribute.displayName}
                          size="small"
                          InputProps={{ readOnly: true }}
                        />
                      ))}
                    </Stack>
                  </FormControl>
                )}
                {isListAttributeSchema(schemaQuery.data) && (
                  <FormControl>
                    <FormLabel component="legend">Attribute</FormLabel>
                    <Stack spacing={1}>
                      <TextField
                        value={schemaQuery.data.attribute.displayName}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </Stack>
                  </FormControl>
                )}
                {isUnionAttributeSchema(schemaQuery.data) && (
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
                )}
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
