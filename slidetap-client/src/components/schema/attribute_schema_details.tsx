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

import { Close } from '@mui/icons-material'
import {
  Card,
  CardContent,
  CardHeader,
  FormControlLabel,
  IconButton,
  LinearProgress,
  Radio,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import OutlinedFormControl from 'src/components/attribute/outlined_form_control'
import ChipDivider from 'src/components/item/chip_divider'
import Spinner from 'src/components/spinner'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
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
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import { ItemSchema } from 'src/models/schema/item_schema'
import schemaApi from 'src/services/api/schema_api'
import { queryKeys } from 'src/services/query_keys'
import SchemaChips, { type SchemaChipEntry } from './schema_chips'

interface DisplayAttributeSchemaDetailsProps {
  schemaUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  /** Open the details of an attribute schema nested in the attribute schema. */
  openAttributeSchema: (attributeSchemaUid: string) => void
  /** Open the details of an item schema that uses the attribute schema. */
  openItemSchema: (itemSchemaUid: string) => void
}

function toEntries(attributes: AttributeSchema[]): SchemaChipEntry[] {
  return attributes.map((attribute) => ({
    uid: attribute.uid,
    title: attribute.displayName,
    description: attribute.description,
  }))
}

/** Return the attribute schemas the given schema directly contains. */
function childAttributes(schema: AttributeSchema): AttributeSchema[] {
  if (isObjectAttributeSchema(schema)) {
    return Object.values(schema.attributes)
  }
  if (isListAttributeSchema(schema)) {
    return [schema.attribute]
  }
  if (isUnionAttributeSchema(schema)) {
    return schema.attributes
  }
  return []
}

export default function DisplayAttributeSchemaDetails({
  schemaUid,
  setOpen,
  openAttributeSchema,
  openItemSchema,
}: DisplayAttributeSchemaDetailsProps): ReactElement {
  const rootSchema = useSchemaContext()
  const allAttributesQuery = useQuery({
    queryKey: queryKeys.schema.attributes(),
    queryFn: async () => {
      return await schemaApi.getAttributeSchemas()
    },
  })
  const schemaQuery = useQuery({
    queryKey: queryKeys.schema.attribute(schemaUid || ''),
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

  // The item and attribute schemas that directly hold this attribute schema.
  // A schema nested deeper is reached by following the chain of usages.
  const itemSchemas: ItemSchema[] = [
    ...Object.values(rootSchema.samples ?? {}),
    ...Object.values(rootSchema.images ?? {}),
    ...Object.values(rootSchema.observations ?? {}),
    ...Object.values(rootSchema.annotations ?? {}),
  ]
  const usedByItems = itemSchemas
    .filter((itemSchema) =>
      [
        ...Object.values(itemSchema.attributes),
        ...Object.values(itemSchema.privateAttributes),
      ].some((attribute) => attribute.uid === schemaUid),
    )
    .map((itemSchema) => ({ uid: itemSchema.uid, title: itemSchema.displayName }))
  const usedByAttributes = toEntries(
    (allAttributesQuery.data ?? []).filter((attributeSchema) =>
      childAttributes(attributeSchema).some((attribute) => attribute.uid === schemaUid),
    ),
  )
  // The project and dataset schemas hold attributes without being items, and
  // have no details of their own to open, so they are listed but not clickable.
  const usedByProjectOrDataset = [
    { type: 'Project', schema: rootSchema.project },
    { type: 'Dataset', schema: rootSchema.dataset },
  ]
    .filter(({ schema }) =>
      [
        ...Object.values(schema.attributes),
        ...Object.values(schema.privateAttributes),
      ].some((attribute) => attribute.uid === schemaUid),
    )
    .map(({ type, schema }) => ({
      uid: schema.uid,
      title: `${type}: ${schema.displayName}`,
    }))

  return (
    <Spinner loading={schemaQuery.isLoading}>
      <Card>
        <CardHeader
          title={schemaQuery.data.displayName}
          action={
            <Tooltip title="Close">
              <IconButton onClick={handleClose} size="small">
                <Close fontSize="small" />
              </IconButton>
            </Tooltip>
          }
        />
        <CardContent>
          <Stack direction="column" spacing={1}>
            {schemaQuery.data.description !== null && (
              <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                {schemaQuery.data.description}
              </Typography>
            )}
            <Stack
              spacing={1}
              direction="row"
              sx={{ alignItems: 'center', flexWrap: 'wrap' }}
            >
              <OutlinedFormControl label="Type">
                <Typography variant="body2">
                  {AttributeValueTypeStrings[schemaQuery.data.attributeValueType]}
                </Typography>
              </OutlinedFormControl>
              <FormControlLabel
                label="Optional"
                control={<Radio readOnly={true} size="small" />}
                checked={schemaQuery.data.optional}
              />
              <FormControlLabel
                label="Read only"
                control={<Radio readOnly={true} size="small" />}
                checked={schemaQuery.data.readOnly}
              />
            </Stack>
            {isEnumAttributeSchema(schemaQuery.data) && (
              <SchemaChips
                label="Allowed values"
                entries={(schemaQuery.data.allowedValues ?? []).map((value) => ({
                  uid: value,
                  title: value,
                }))}
              />
            )}
            {isDatetimeAttributeSchema(schemaQuery.data) && (
              <OutlinedFormControl label="Datetime type" fullWidth>
                <Typography variant="body2">
                  {DatetimeTypeStrings[schemaQuery.data.datetimeType]}
                </Typography>
              </OutlinedFormControl>
            )}
            {isNumericAttributeSchema(schemaQuery.data) && (
              <FormControlLabel
                label="Is integer"
                control={<Radio readOnly={true} />}
                checked={schemaQuery.data.isInteger}
              />
            )}
            {isMeasurementAttributeSchema(schemaQuery.data) && (
              <SchemaChips
                label="Allowed units"
                entries={(schemaQuery.data.allowedUnits ?? []).map((unit) => ({
                  uid: unit,
                  title: unit,
                }))}
              />
            )}
            {isCodeAttributeSchema(schemaQuery.data) && (
              <SchemaChips
                label="Allowed schemas"
                entries={(schemaQuery.data.allowedSchemas ?? []).map((schema) => ({
                  uid: schema,
                  title: schema,
                }))}
              />
            )}
            {isObjectAttributeSchema(schemaQuery.data) && (
              <SchemaChips
                label="Attributes"
                entries={toEntries(Object.values(schemaQuery.data.attributes))}
                onClick={openAttributeSchema}
              />
            )}
            {isListAttributeSchema(schemaQuery.data) && (
              <SchemaChips
                label="Attribute"
                entries={toEntries([schemaQuery.data.attribute])}
                onClick={openAttributeSchema}
              />
            )}
            {isUnionAttributeSchema(schemaQuery.data) && (
              <SchemaChips
                label="Attributes"
                entries={toEntries(schemaQuery.data.attributes)}
                onClick={openAttributeSchema}
              />
            )}
            {(usedByItems.length > 0 ||
              usedByAttributes.length > 0 ||
              usedByProjectOrDataset.length > 0) && (
              <ChipDivider label="Used by" color="default" />
            )}
            {usedByProjectOrDataset.length > 0 && (
              <SchemaChips
                label="Project and dataset"
                entries={usedByProjectOrDataset}
              />
            )}
            {usedByItems.length > 0 && (
              <SchemaChips
                label="Items"
                entries={usedByItems}
                onClick={openItemSchema}
              />
            )}
            {usedByAttributes.length > 0 && (
              <SchemaChips
                label="Attributes"
                entries={usedByAttributes}
                onClick={openAttributeSchema}
              />
            )}
          </Stack>
        </CardContent>
      </Card>
    </Spinner>
  )
}
