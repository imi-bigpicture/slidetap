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
  LinearProgress,
  Stack,
  TextField,
} from '@mui/material'
import Grid from '@mui/material/Grid'
import { useQuery } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import DisplayAttribute from 'src/components/attribute/display_attribute'
import NestedAttributeDetails from 'src/components/attribute/nested_attribute_details'
import Spinner from 'src/components/spinner'
import { ItemDetailAction } from 'src/models/action'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import mappingApi from 'src/services/api/mapper_api'
import schemaApi from 'src/services/api/schema_api'

interface MappingDetailsProps {
  mappingUid: string | undefined
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function MappingDetails({
  mappingUid,
  setOpen,
}: MappingDetailsProps): ReactElement {
  const [openedAttributes, setOpenedAttributes] = useState<
    Array<{
      schema: AttributeSchema
      attribute: Attribute<AttributeValueTypes>
      updateAttribute: (
        tag: string,
        attribute: Attribute<AttributeValueTypes>,
      ) => Attribute<AttributeValueTypes>
    }>
  >([])
  const mappingQuery = useQuery({
    queryKey: ['mapping', mappingUid],
    queryFn: async () => {
      if (mappingUid === undefined) {
        return undefined
      }
      return await mappingApi.getMapping(mappingUid)
    },
    enabled: mappingUid !== undefined,
  })
  const schemaQuery = useQuery({
    queryKey: ['attributeSchema', mappingQuery?.data?.attribute.schemaUid],
    queryFn: async () => {
      if (mappingQuery.data === undefined) {
        return undefined
      }
      return await schemaApi.getAttributeSchema(mappingQuery.data.attribute.schemaUid)
    },
  })
  if (mappingQuery.data === undefined || schemaQuery.data === undefined) {
    return <LinearProgress />
  }

  const handleAttributeOpen = (
    schema: AttributeSchema,
    attribute: Attribute<AttributeValueTypes>,
    updateAttribute: (
      tag: string,
      attribute: Attribute<AttributeValueTypes>,
    ) => Attribute<AttributeValueTypes>,
  ): void => {
    setOpenedAttributes([...openedAttributes, { schema, attribute, updateAttribute }])
  }

  const handleNestedAttributeChange = (uid?: string): void => {
    if (uid === undefined) {
      setOpenedAttributes([])
      return
    }
    const parentAttributeIndex = openedAttributes.findIndex(
      (attribute) => attribute.attribute.uid === uid,
    )
    if (parentAttributeIndex >= 0) {
      setOpenedAttributes(openedAttributes.slice(0, parentAttributeIndex + 1))
    }
  }

  const handleClose = (): void => {
    setOpen(false)
  }
  const handleSave = (): void => {}

  return (
    <Spinner loading={mappingQuery.isLoading}>
      <Card>
        <CardHeader title="Mapping" />
        <CardContent>
          <Grid container spacing={1}>
            <Grid size={{ xs: 12 }}>
              {openedAttributes.length === 0 && (
                <Stack spacing={1} direction={'column'}>
                  <TextField label="Expression" value={mappingQuery.data.expression} />
                  <Stack spacing={1}>
                    <DisplayAttribute
                      attribute={mappingQuery.data.attribute}
                      schema={schemaQuery.data}
                      action={ItemDetailAction.VIEW}
                      handleAttributeUpdate={() => {}}
                      handleAttributeOpen={handleAttributeOpen}
                    />
                  </Stack>
                </Stack>
              )}
              {openedAttributes.length > 0 && (
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  action={ItemDetailAction.VIEW}
                  handleNestedAttributeChange={handleNestedAttributeChange}
                  handleAttributeOpen={handleAttributeOpen}
                  handleAttributeUpdate={() => {}}
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
