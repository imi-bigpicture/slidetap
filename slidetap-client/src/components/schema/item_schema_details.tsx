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
  IconButton,
  LinearProgress,
  Stack,
  Tooltip,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import OutlinedFormControl from 'src/components/attribute/outlined_form_control'
import ChipDivider from 'src/components/item/chip_divider'
import Spinner from 'src/components/spinner'
import { isImageSchema, isObservationSchema, isSampleSchema } from 'src/models/helpers'
import { ItemValueTypeStrings } from 'src/models/item_value_type'
import schemaApi from 'src/services/api/schema_api'
import { queryKeys } from 'src/services/query_keys'
import SchemaChips from './schema_chips'

interface DisplayItemSchemaDetailsProps {
  schemaUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  /** Open the details of one of the attribute schemas of the item schema. */
  openAttributeSchema: (attributeSchemaUid: string) => void
  /** Open the details of an item schema the item schema is related to. */
  openItemSchema: (itemSchemaUid: string) => void
}

export default function DisplayItemSchemaDetails({
  schemaUid,
  setOpen,
  openAttributeSchema,
  openItemSchema,
}: DisplayItemSchemaDetailsProps): ReactElement {
  const schemaQuery = useQuery({
    queryKey: queryKeys.schema.item(schemaUid || ''),
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
            <OutlinedFormControl label="Type" fullWidth>
              <Typography variant="body2">
                {ItemValueTypeStrings[schemaQuery.data.itemValueType]}
              </Typography>
            </OutlinedFormControl>
            <ChipDivider label="Relations" color="default" />
            {isSampleSchema(schemaQuery.data) && (
              <>
                <SchemaChips
                  label="Parents"
                  entries={schemaQuery.data.parents.map((parent) => ({
                    uid: parent.parentUid,
                    title: parent.parentTitle,
                  }))}
                  onClick={openItemSchema}
                />
                <SchemaChips
                  label="Children"
                  entries={schemaQuery.data.children.map((child) => ({
                    uid: child.childUid,
                    title: child.childTitle,
                  }))}
                  onClick={openItemSchema}
                />
                <SchemaChips
                  label="Images"
                  entries={schemaQuery.data.images.map((image) => ({
                    uid: image.imageUid,
                    title: image.imageTitle,
                  }))}
                  onClick={openItemSchema}
                />
                <SchemaChips
                  label="Observations"
                  entries={schemaQuery.data.observations.map((observation) => ({
                    uid: observation.observationUid,
                    title: observation.observationTitle,
                  }))}
                  onClick={openItemSchema}
                />
              </>
            )}
            {isImageSchema(schemaQuery.data) && (
              <>
                <SchemaChips
                  label="Samples"
                  entries={schemaQuery.data.samples.map((sample) => ({
                    uid: sample.sampleUid,
                    title: sample.sampleTitle,
                  }))}
                  onClick={openItemSchema}
                />
                <SchemaChips
                  label="Observations"
                  entries={schemaQuery.data.observations.map((observation) => ({
                    uid: observation.observationUid,
                    title: observation.observationTitle,
                  }))}
                  onClick={openItemSchema}
                />
              </>
            )}
            {isObservationSchema(schemaQuery.data) && (
              <>
                <SchemaChips
                  label="Samples"
                  entries={schemaQuery.data.samples.map((sample) => ({
                    uid: sample.sampleUid,
                    title: sample.sampleTitle,
                  }))}
                  onClick={openItemSchema}
                />
                <SchemaChips
                  label="Images"
                  entries={schemaQuery.data.images.map((image) => ({
                    uid: image.imageUid,
                    title: image.imageTitle,
                  }))}
                  onClick={openItemSchema}
                />
              </>
            )}
            <ChipDivider label="Attributes" color="default" />
            <SchemaChips
              label="Attributes"
              entries={Object.values(schemaQuery.data.attributes).map((attribute) => ({
                uid: attribute.uid,
                title: attribute.displayName,
              }))}
              onClick={openAttributeSchema}
            />
            {Object.values(schemaQuery.data.privateAttributes).length > 0 && (
              <SchemaChips
                label="Private attributes"
                entries={Object.values(schemaQuery.data.privateAttributes).map(
                  (attribute) => ({
                    uid: attribute.uid,
                    title: attribute.displayName,
                  }),
                )}
                onClick={openAttributeSchema}
              />
            )}
          </Stack>
        </CardContent>
      </Card>
    </Spinner>
  )
}
