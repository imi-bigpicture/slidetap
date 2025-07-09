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

import { TabContext, TabList, TabPanel } from '@mui/lab'
import { Tab } from '@mui/material'
import Grid from '@mui/material/Grid'
import { useQuery } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import { BasicTable } from 'src/components/table/basic_table'
import { Action } from 'src/models/action'
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import { ItemSchema } from 'src/models/schema/item_schema'
import schemaApi from 'src/services/api/schema_api'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import DisplayAttributeSchemaDetails from './attribute_schema_details'
import DisplayItemSchemaDetails from './item_schema_details'

export default function ListSchemas(): ReactElement {
  const [attributeSchemaDetailsOpen, setAttributeSchemaDetailsOpen] =
    React.useState(false)
  const [attributeSchemaDetailUid, setAttributeSchemaDetailUid] =
    React.useState<string>()

  const [itemSchemaDetailsOpen, setItemSchemaDetailsOpen] = React.useState(false)
  const [itemSchemaDetailUid, setItemSchemaDetailUid] = React.useState<string>()
  const [tabValue, setTabValue] = useState(0)

  const attributeSchemasQuery = useQuery({
    queryKey: ['attributeSchemas'],
    queryFn: async () => {
      return await schemaApi.getAttributeSchemas()
    },
  })
  const rootSchema = useSchemaContext()

  const handleAttributeAction = (schema: AttributeSchema): void => {
    setAttributeSchemaDetailUid(schema.uid)
    setItemSchemaDetailsOpen(false)
    setAttributeSchemaDetailsOpen(true)
  }

  const handleItemAction = (schema: ItemSchema): void => {
    setItemSchemaDetailUid(schema.uid)
    setAttributeSchemaDetailsOpen(false)
    setItemSchemaDetailsOpen(true)
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid size={{ xs: 8 }}>
        <TabContext value={tabValue}>
          <TabList onChange={(_, newValue) => setTabValue(newValue)}>
            <Tab label="Items" />
            <Tab label="Attributes" />
          </TabList>
          <TabPanel value={0}>
            <BasicTable<ItemSchema>
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
              data={Object.values(rootSchema.samples ?? {})}
              rowsSelectable={false}
              actions={[{ action: Action.VIEW, onAction: handleItemAction }]}
            />
          </TabPanel>
          <TabPanel value={1}>
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
              data={attributeSchemasQuery.data ?? []}
              rowsSelectable={false}
              actions={[{ action: Action.VIEW, onAction: handleAttributeAction }]}
              isLoading={attributeSchemasQuery.isLoading}
            />
          </TabPanel>
        </TabContext>
      </Grid>
      {attributeSchemaDetailsOpen && (
        <Grid size={{ xs: 4 }}>
          <DisplayAttributeSchemaDetails
            schemaUid={attributeSchemaDetailUid}
            setOpen={setAttributeSchemaDetailsOpen}
          />
        </Grid>
      )}
      {itemSchemaDetailsOpen && (
        <Grid size={{ xs: 4 }}>
          <DisplayItemSchemaDetails
            schemaUid={itemSchemaDetailUid}
            setOpen={setItemSchemaDetailsOpen}
          />
        </Grid>
      )}
    </Grid>
  )
}
