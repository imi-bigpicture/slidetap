import {
  Button,
  Card,
  CardActions,
  CardContent,
  CardHeader,
  FormControl,
  FormControlLabel,
  FormLabel,
  Radio,
  Stack,
  TextField,
} from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import Spinner from 'components/spinner'
import { AttributeValueTypeStrings, DatetimeTypeStrings } from 'models/attribute'
import {
  isCodeAttributeSchema,
  isDatetimeAttributeSchema,
  isEnumAttributeSchema,
  isListAttributeSchema,
  isMeasurementAttributeSchema,
  isNumericAttributeSchema,
  isObjectAttributeSchema,
  isUnionAttributeSchema,
} from 'models/helpers'
import type { AttributeSchema } from 'models/schema'
import React, { useEffect, useState, type ReactElement } from 'react'
import schemaApi from 'services/api/schema_api'

interface DisplayAttributeSchemaDetailsProps {
  schemaUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function DisplayAttributeSchemaDetails({
  schemaUid,
  setOpen,
}: DisplayAttributeSchemaDetailsProps): ReactElement {
  const [currentSchemaUid, setCurrentSchemaUid] = useState<string | undefined>(
    schemaUid,
  )
  const [schema, setSchema] = useState<AttributeSchema>()
  const [isLoading, setIsLoading] = useState<boolean>(true)

  useEffect(() => {
    const getSchema = (schemaUid: string): void => {
      schemaApi
        .getAttributeSchema(schemaUid)
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
                    value={AttributeValueTypeStrings[schema.attributeValueType]}
                    size="small"
                    InputProps={{ readOnly: true }}
                  />
                </FormControl>
                <Stack spacing={1} direction="row" justifyContent="space-evenly">
                  <FormControlLabel
                    label="Optional"
                    control={<Radio readOnly={true} />}
                    checked={schema.optional}
                  />
                  <FormControlLabel
                    label="Read only"
                    control={<Radio readOnly={true} />}
                    checked={schema.readOnly}
                  />
                </Stack>
                {isEnumAttributeSchema(schema) && (
                  <FormControl>
                    <FormLabel component="legend">Allowed values</FormLabel>
                    <TextField
                      value={schema.allowedValues}
                      size="small"
                      InputProps={{ readOnly: true }}
                    />
                  </FormControl>
                )}
                {isDatetimeAttributeSchema(schema) && (
                  <FormControl>
                    <FormLabel component="legend">Datetime type</FormLabel>
                    <TextField
                      value={DatetimeTypeStrings[schema.datetimeType]}
                      size="small"
                      InputProps={{ readOnly: true }}
                    />
                  </FormControl>
                )}
                {isNumericAttributeSchema(schema) && (
                  <FormControlLabel
                    label="Is integer"
                    control={<Radio readOnly={true} />}
                    checked={schema.isInt}
                  />
                )}
                {isMeasurementAttributeSchema(schema) && (
                  <FormControl>
                    <FormLabel component="legend">Allowed units</FormLabel>
                    <TextField
                      value={schema.allowedUnits}
                      size="small"
                      InputProps={{ readOnly: true }}
                    />
                  </FormControl>
                )}
                {isCodeAttributeSchema(schema) && (
                  <FormControl>
                    <FormLabel component="legend">Allowed schemas</FormLabel>
                    <TextField
                      value={schema.allowedSchemas ?? ''}
                      size="small"
                      InputProps={{ readOnly: true }}
                    />
                  </FormControl>
                )}
                {isObjectAttributeSchema(schema) && (
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
                )}
                {isListAttributeSchema(schema) && (
                  <FormControl>
                    <FormLabel component="legend">Attribute</FormLabel>
                    <Stack spacing={1}>
                      <TextField
                        value={schema.attribute.displayName}
                        size="small"
                        InputProps={{ readOnly: true }}
                      />
                    </Stack>
                  </FormControl>
                )}
                {isUnionAttributeSchema(schema) && (
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
