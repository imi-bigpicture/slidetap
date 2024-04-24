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

import { Stack, Tab, Tabs } from '@mui/material'
import Grid from '@mui/material/Unstable_Grid2/Grid2'
import { BasicTable } from 'components/table/basic_table'
import type { Action } from 'models/action'
import { AttributeValueTypeStrings } from 'models/attribute'
import type { AttributeSchema, ItemSchema } from 'models/schema'
import React, { useEffect, useState, type ReactElement } from 'react'
import schemaApi from 'services/api/schema_api'
import DisplayAttributeSchemaDetails from './attribute_schema_details'
import DisplayItemSchemaDetails from './item_schema_details'

const rootSchemaUid = 'be6232ba-76fe-40d8-af4a-76a29eb85b3a'

export default function DisplaySchemas(): ReactElement {
  const [attributeSchemas, setAttributeSchemas] = useState<AttributeSchema[]>([])
  const [itemSchemas, setItemSchemas] = useState<ItemSchema[]>([])

  const [isLoading, setIsLoading] = useState<boolean>(true)
  const [attributeSchemaDetailsOpen, setAttributeSchemaDetailsOpen] =
    React.useState(false)
  const [attributeSchemaDetailUid, setAttributeSchemaDetailUid] =
    React.useState<string>()

  const [itemSchemaDetailsOpen, setItemSchemaDetailsOpen] = React.useState(false)
  const [itemSchemaDetailUid, setItemSchemaDetailUid] = React.useState<string>()
  const [tabValue, setTabValue] = useState(0)

  const getAttributeSchemas = (): void => {
    schemaApi
      .getAttributeSchemas(rootSchemaUid)
      .then((schemas) => {
        setAttributeSchemas(schemas)
      })
      .catch((x) => {
        console.error('Failed to get schemas', x)
      })
  }
  const getItemSchemas = (): void => {
    schemaApi
      .getItemSchemas(rootSchemaUid)
      .then((schemas) => {
        setItemSchemas(schemas)
      })
      .catch((x) => {
        console.error('Failed to get schemas', x)
      })
  }

  useEffect(() => {
    setIsLoading(true)
    getAttributeSchemas()
    getItemSchemas()
    setIsLoading(false)
  }, [])

  const handleAttributeAction = (schemaUid: string, action: Action): void => {
    setAttributeSchemaDetailUid(schemaUid)
    setItemSchemaDetailsOpen(false)
    setAttributeSchemaDetailsOpen(true)
  }

  const handleItemAction = (schemaUid: string, action: Action): void => {
    setItemSchemaDetailUid(schemaUid)
    setAttributeSchemaDetailsOpen(false)
    setItemSchemaDetailsOpen(true)
  }

  const handleTabChange = (event: React.SyntheticEvent, newValue: number): void => {
    setTabValue(newValue)
  }
  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid xs={12}>
        <Stack direction="row" spacing={2}></Stack>
      </Grid>
      <Grid xs>
        <Tabs value={tabValue} onChange={handleTabChange}>
          <Tab label="Items" />
          <Tab label="Attributes" />
        </Tabs>
        {tabValue === 1 && (
          <BasicTable
            columns={[
              {
                header: 'Name',
                accessorKey: 'displayName',
              },
              {
                header: 'Type',
                accessorKey: 'attributeValueType',
              },
            ]}
            data={attributeSchemas.map((schema) => {
              return {
                uid: schema.uid,
                displayName: schema.displayName,
                attributeValueType:
                  AttributeValueTypeStrings[schema.attributeValueType],
              }
            })}
            rowsSelectable={false}
            onRowAction={handleAttributeAction}
            isLoading={isLoading}
          />
        )}
        {tabValue === 0 && (
          <BasicTable
            columns={[
              {
                header: 'Name',
                accessorKey: 'displayName',
              },
              // {
              //   header: 'Type',
              //   accessorKey: 'attributeValueType',
              // },
            ]}
            data={itemSchemas.map((schema) => {
              return {
                uid: schema.uid,
                displayName: schema.displayName,
                // attributeValueType:
                //   AttributeValueTypeStrings[schema.attributeValueType],
              }
            })}
            rowsSelectable={false}
            onRowAction={handleItemAction}
            isLoading={isLoading}
          />
        )}
      </Grid>
      {attributeSchemaDetailsOpen && (
        <Grid xs={4}>
          <DisplayAttributeSchemaDetails
            schemaUid={attributeSchemaDetailUid}
            setOpen={setAttributeSchemaDetailsOpen}
          />
        </Grid>
      )}
      {itemSchemaDetailsOpen && (
        <Grid xs={4}>
          <DisplayItemSchemaDetails
            schemaUid={itemSchemaDetailUid}
            setOpen={setItemSchemaDetailsOpen}
          />
        </Grid>
      )}
    </Grid>
  )
}
