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
import { Stack, Tab } from '@mui/material'
import Grid from '@mui/material/Grid'
import { useQuery } from '@tanstack/react-query'
import React, { useState, type ReactElement } from 'react'
import { BasicTable } from 'src/components/table/basic_table'
import { Action } from 'src/models/action'
import { AttributeValueTypeStrings } from 'src/models/attribute_value_type'
import { ItemValueTypeStrings } from 'src/models/item_value_type'
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import { ItemSchema } from 'src/models/schema/item_schema'
import schemaApi from 'src/services/api/schema_api'
import { queryKeys } from 'src/services/query_keys'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import DisplayAttributeSchemaDetails from './attribute_schema_details'
import DisplayItemSchemaDetails from './item_schema_details'
import ProjectAndDatasetSchemas from './project_dataset_schemas'

export default function ListSchemas(): ReactElement {
  const [attributeSchemaDetailsOpen, setAttributeSchemaDetailsOpen] =
    React.useState(false)
  const [attributeSchemaDetailUid, setAttributeSchemaDetailUid] =
    React.useState<string>()

  const [itemSchemaDetailsOpen, setItemSchemaDetailsOpen] = React.useState(false)
  const [itemSchemaDetailUid, setItemSchemaDetailUid] = React.useState<string>()
  const [tabValue, setTabValue] = useState(0)

  const attributeSchemasQuery = useQuery({
    queryKey: queryKeys.schema.attributes(),
    queryFn: async () => {
      return await schemaApi.getAttributeSchemas()
    },
  })
  const rootSchema = useSchemaContext()
  const itemSchemas: ItemSchema[] = [
    ...Object.values(rootSchema.samples ?? {}),
    ...Object.values(rootSchema.images ?? {}),
    ...Object.values(rootSchema.observations ?? {}),
    ...Object.values(rootSchema.annotations ?? {}),
  ]

  // Navigating from a panel keeps the other panel open, so that an attribute
  // opened from an item schema is shown below the item schema it belongs to.
  const openAttributeSchema = (schemaUid: string): void => {
    setAttributeSchemaDetailUid(schemaUid)
    setAttributeSchemaDetailsOpen(true)
  }

  const openItemSchema = (schemaUid: string): void => {
    setItemSchemaDetailUid(schemaUid)
    setItemSchemaDetailsOpen(true)
  }

  // Picking from a table starts over, so that the panels never show a schema
  // left over from what was looked at before.
  const handleAttributeAction = (schema: AttributeSchema): void => {
    setItemSchemaDetailsOpen(false)
    openAttributeSchema(schema.uid)
  }

  const handleItemAction = (schema: ItemSchema): void => {
    setAttributeSchemaDetailsOpen(false)
    openItemSchema(schema.uid)
  }

  return (
    // The tabs are above the columns, and the tab panels hold no padding of
    // their own, so that the table lines up with the detail panel beside it.
    <TabContext value={tabValue}>
      <TabList onChange={(_, newValue) => setTabValue(newValue)}>
        <Tab label="Items" />
        <Tab label="Attributes" />
        <Tab label="Project and dataset" />
      </TabList>
      <Grid
        container
        spacing={1}
        sx={{ justifyContent: 'flex-start', alignItems: 'flex-start' }}
      >
        <Grid size={{ xs: 8 }}>
          <TabPanel value={0} sx={{ p: 0 }}>
            <BasicTable<ItemSchema>
              columns={[
                {
                  header: 'Name',
                  accessorKey: 'displayName',
                },
                {
                  header: 'Type',
                  id: 'itemValueType',
                  accessorFn: (schema) => ItemValueTypeStrings[schema.itemValueType],
                },
              ]}
              data={itemSchemas}
              rowsSelectable={false}
              actions={[{ action: Action.VIEW, onAction: handleItemAction }]}
            />
          </TabPanel>
          <TabPanel value={1} sx={{ p: 0 }}>
            <BasicTable<AttributeSchema>
              columns={[
                {
                  header: 'Name',
                  accessorKey: 'displayName',
                },
                {
                  header: 'Type',
                  id: 'attributeValueType',
                  accessorFn: (schema) =>
                    AttributeValueTypeStrings[schema.attributeValueType],
                },
              ]}
              data={attributeSchemasQuery.data ?? []}
              rowsSelectable={false}
              actions={[{ action: Action.VIEW, onAction: handleAttributeAction }]}
              isLoading={attributeSchemasQuery.isLoading}
            />
          </TabPanel>
          <TabPanel value={2} sx={{ p: 0 }}>
            <ProjectAndDatasetSchemas openAttributeSchema={openAttributeSchema} />
          </TabPanel>
        </Grid>
        {(itemSchemaDetailsOpen || attributeSchemaDetailsOpen) && (
          <Grid size={{ xs: 4 }}>
            <Stack spacing={1}>
              {itemSchemaDetailsOpen && (
                <DisplayItemSchemaDetails
                  schemaUid={itemSchemaDetailUid}
                  setOpen={setItemSchemaDetailsOpen}
                  openAttributeSchema={openAttributeSchema}
                  openItemSchema={openItemSchema}
                />
              )}
              {attributeSchemaDetailsOpen && (
                <DisplayAttributeSchemaDetails
                  schemaUid={attributeSchemaDetailUid}
                  setOpen={setAttributeSchemaDetailsOpen}
                  openAttributeSchema={openAttributeSchema}
                  openItemSchema={openItemSchema}
                />
              )}
            </Stack>
          </Grid>
        )}
      </Grid>
    </TabContext>
  )
}
