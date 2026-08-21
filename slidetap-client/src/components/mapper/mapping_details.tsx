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
  Alert,
  Button,
  Card,
  CardActions,
  CardContent,
  CardHeader,
  LinearProgress,
  Stack,
  TextField,
  Typography,
} from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import DisplayAttribute from 'src/components/attribute/display_attribute'
import NestedAttributeDetails from 'src/components/attribute/nested_attribute_details'
import Spinner from 'src/components/spinner'
import { useError } from 'src/contexts/error/error_context'
import { ItemDetailAction } from 'src/models/action'
import {
  RejectedValues,
  type Attribute,
  type AttributeValueTypes,
} from 'src/models/attribute'
import type { Mapper } from 'src/models/mapper'
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import mapperApi from 'src/services/api/mapper_api'
import schemaApi from 'src/services/api/schema_api'
import { queryKeys } from 'src/services/query_keys'

const NIL_UID = '00000000-0000-0000-0000-000000000000'

function emptyAttribute(schema: AttributeSchema): Attribute<AttributeValueTypes> {
  return {
    uid: NIL_UID,
    schemaUid: schema.uid,
    originalValue: null,
    updatedValue: null,
    mappedValue: null,
    valid: false,
    displayValue: '',
    mappableValue: null,
    mappingItemUid: null,
    rejected: RejectedValues.NONE,
    attributeValueType: schema.attributeValueType,
  }
}

interface MappingDetailsProps {
  mapper: Mapper
  /** Mapping to edit. If not set a new mapping is created. */
  mappingUid: string | undefined
  /** What a new mapping starts with as its expression.
   *
   * Set when the mapping is being added for a value that was found waiting for
   * one, so that what the laboratory wrote is what the key is written from
   * rather than being typed again from the list. */
  initialExpression?: string
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
}

export default function MappingDetails({
  mapper,
  mappingUid,
  initialExpression,
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
  const [expression, setExpression] = useState<string>('')
  const [attribute, setAttribute] = useState<Attribute<AttributeValueTypes>>()
  const { showError } = useError()
  const queryClient = useQueryClient()

  const mappingQuery = useQuery({
    queryKey: queryKeys.mapping.detail(mappingUid ?? ''),
    queryFn: async () => {
      if (mappingUid === undefined) {
        return undefined
      }
      return await mapperApi.getMapping(mappingUid)
    },
    enabled: mappingUid !== undefined,
  })
  // An existing mapping is displayed with the schema of its own attribute, a new
  // one with the schema the mapper maps.
  const schemaUid = mappingQuery.data?.attribute.schemaUid ?? mapper.attributeSchemaUid
  const schemaQuery = useQuery({
    queryKey: queryKeys.schema.attribute(schemaUid),
    queryFn: async () => {
      return await schemaApi.getAttributeSchema(schemaUid)
    },
    enabled: mappingUid === undefined || mappingQuery.data !== undefined,
  })

  // Seed the form from the loaded mapping, or from an empty attribute when new.
  React.useEffect(() => {
    if (mappingUid === undefined) {
      setExpression(initialExpression ?? '')
      setAttribute(
        schemaQuery.data === undefined ? undefined : emptyAttribute(schemaQuery.data),
      )
    } else if (mappingQuery.data !== undefined) {
      setExpression(mappingQuery.data.expression)
      setAttribute(mappingQuery.data.attribute)
    }
    setOpenedAttributes([])
  }, [mappingUid, mappingQuery.data, schemaQuery.data, initialExpression])

  // What else already resolves to this, so that a seventh spelling of the same
  // thing is added knowing it is the seventh. Compared on the display value:
  // the mapper holds attributes of any type, and what a curator recognises a
  // target by is what they see.
  const siblingsQuery = useQuery({
    queryKey: queryKeys.mapper.mappings(mapper.uid),
    queryFn: async () => {
      return await mapperApi.getMappings(mapper.uid)
    },
  })
  const target = attribute?.displayValue
  const siblings =
    target === undefined || target === null || target === ''
      ? []
      : (siblingsQuery.data ?? []).filter(
          (mapping) =>
            mapping.uid !== mappingUid && mapping.attribute.displayValue === target,
        )

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (attribute === undefined) {
        throw new Error('No attribute to save')
      }
      if (mappingQuery.data !== undefined) {
        return await mapperApi.updateMapping({
          ...mappingQuery.data,
          expression,
          attribute,
        })
      }
      return await mapperApi.createMapping({
        mapperUid: mapper.uid,
        expression,
        attribute,
      })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mapper.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.mapping.all })
      setOpen(false)
    },
    onError: (error) => {
      showError('Failed to save mapping', error)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: async () => {
      if (mappingUid === undefined) {
        return
      }
      return await mapperApi.deleteMapping(mappingUid)
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.mapper.all })
      void queryClient.invalidateQueries({ queryKey: queryKeys.mapping.all })
      setOpen(false)
    },
    onError: (error) => {
      showError('Failed to delete mapping', error)
    },
  })

  if (schemaQuery.data === undefined || attribute === undefined) {
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

  const handleAttributeUpdate = (
    _tag: string,
    updated: Attribute<AttributeValueTypes>,
  ): void => {
    setAttribute(updated)
  }

  const handleClose = (): void => {
    setOpen(false)
  }
  const handleDelete = (): void => {
    // ponytail: native confirm, swap for a dialog if the design calls for one.
    if (!window.confirm(`Delete mapping "${expression}"?`)) {
      return
    }
    deleteMutation.mutate()
  }

  return (
    <Spinner loading={mappingQuery.isLoading}>
      <Card>
        <CardHeader title="Mapping" />
        <CardContent>
          <Grid container spacing={1}>
            <Grid size={{ xs: 12 }}>
              {openedAttributes.length === 0 && (
                <Stack spacing={1} direction={'column'}>
                  <TextField
                    label="Expression"
                    value={expression}
                    onChange={(event) => {
                      setExpression(event.target.value)
                    }}
                  />
                  {siblings.length > 0 && (
                    <Alert severity="info" icon={false}>
                      <Typography variant="body2">
                        {`Already resolving to ${target}:`}
                      </Typography>
                      <Typography variant="body2">
                        {siblings.map((sibling) => sibling.expression).join(', ')}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Widening one of those covers this wording too, and
                        leaves one key to read rather than two.
                      </Typography>
                    </Alert>
                  )}
                  <Stack spacing={1}>
                    <DisplayAttribute
                      attribute={attribute}
                      schema={schemaQuery.data}
                      action={ItemDetailAction.EDIT}
                      handleAttributeUpdate={handleAttributeUpdate}
                      handleAttributeOpen={handleAttributeOpen}
                    />
                  </Stack>
                </Stack>
              )}
              {openedAttributes.length > 0 && (
                <NestedAttributeDetails
                  openedAttributes={openedAttributes}
                  action={ItemDetailAction.EDIT}
                  handleNestedAttributeChange={handleNestedAttributeChange}
                  handleAttributeOpen={handleAttributeOpen}
                  handleAttributeUpdate={handleAttributeUpdate}
                />
              )}
            </Grid>
          </Grid>
        </CardContent>
        <CardActions disableSpacing>
          <Button
            onClick={() => saveMutation.mutate()}
            disabled={expression === '' || saveMutation.isPending}
          >
            Save
          </Button>
          {mappingUid !== undefined && (
            <Button onClick={handleDelete} disabled={deleteMutation.isPending}>
              Delete
            </Button>
          )}
          <Button onClick={handleClose}>Close</Button>
        </CardActions>
      </Card>
    </Spinner>
  )
}
