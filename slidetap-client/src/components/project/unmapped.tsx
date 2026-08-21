//    Copyright 2026 SECTRA AB
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
import { FileDownload } from '@mui/icons-material'
import { Button, Typography } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import SplitPanel from 'src/components/split_panel'
import { BasicTable } from 'src/components/table/basic_table'
import { Action } from 'src/models/action'
import type { Batch } from 'src/models/batch'
import type { Mapper, UnmappedValue } from 'src/models/mapper'
import type { Project } from 'src/models/project'
import mapperApi from 'src/services/api/mapper_api'
import { queryKeys } from 'src/services/query_keys'
import MappingDetails from 'src/components/mapper/mapping_details'

interface UnmappedProps {
  project: Project
  /** Only what is on items in this batch, when the batch view is open. */
  batch?: Batch
}

/** A value with the row identity the table needs.
 *
 * A wording is not a thing the database keeps: it is written down once per
 * attribute carrying it, and counted when read. The table wants a key per row
 * all the same, and what makes a row here is the attribute and the wording.
 */
interface UnmappedRow extends UnmappedValue {
  uid: string
}

/** One attribute's worth of wordings, as the exported file holds them. */
interface ExportedAttribute {
  attribute: string
  attributeSchemaUid: string
  values: string[]
}

export default function Unmapped({ project, batch }: UnmappedProps): ReactElement {
  const [addMappingOpen, setAddMappingOpen] = React.useState(false)
  const [mappingFor, setMappingFor] = React.useState<UnmappedRow>()

  const unmappedQuery = useQuery({
    queryKey: queryKeys.mapper.unmapped(project.uid, batch?.uid),
    queryFn: async () => {
      return await mapperApi.getUnmappedValues(project.uid, batch?.uid)
    },
  })
  const mappersQuery = useQuery({
    queryKey: queryKeys.mapper.list(),
    queryFn: async () => {
      return await mapperApi.getMappers()
    },
  })

  const rows: UnmappedRow[] = (unmappedQuery.data ?? []).map((unmapped) => ({
    ...unmapped,
    uid: `${unmapped.attributeSchemaUid}|${unmapped.value}`,
  }))
  const mapperFor = (row: UnmappedRow): Mapper | undefined =>
    mappersQuery.data?.find((mapper) => mapper.uid === row.mapperUid)

  /** What is on screen, as something to hand to whoever writes the keys.
   *
   * Grouped by attribute, since a wording only means anything against the
   * attribute it was recorded for, and the same wording under two attributes
   * is two decisions.
   */
  const exportShown = (rows: UnmappedRow[]): void => {
    const byAttribute = new Map<string, ExportedAttribute>()
    for (const row of rows) {
      const exported = byAttribute.get(row.attributeSchemaUid) ?? {
        attribute: row.displayName,
        attributeSchemaUid: row.attributeSchemaUid,
        values: [],
      }
      exported.values.push(row.value)
      byAttribute.set(row.attributeSchemaUid, exported)
    }
    const scope = batch !== undefined ? batch.name : project.name
    const blob = new Blob([JSON.stringify([...byAttribute.values()], null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `unmapped values ${scope}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const handleAddMapping = (row: UnmappedRow): void => {
    setMappingFor(row)
    setAddMappingOpen(true)
  }

  const openFor = mappingFor !== undefined ? mapperFor(mappingFor) : undefined
  return (
    <SplitPanel
      panel={
        addMappingOpen &&
        openFor !== undefined && (
          <MappingDetails
            mapper={openFor}
            mappingUid={undefined}
            initialExpression={mappingFor?.value}
            setOpen={setAddMappingOpen}
          />
        )
      }
    >
      <BasicTable
        columns={[
          {
            header: 'Attribute',
            accessorKey: 'displayName',
          },
          {
            header: 'Value',
            accessorKey: 'value',
          },
          {
            header: 'Items',
            accessorKey: 'items',
            // What a key would settle, which is what decides where to start.
            size: 80,
          },
          {
            header: 'Mapper',
            id: 'mapper',
            Cell: ({ row }) =>
              row.original.mapperUid !== null ? (
                (mapperFor(row.original)?.name ?? '')
              ) : (
                // Nothing would resolve this wording however it were worded:
                // the attribute has no mapper at all.
                <Typography variant="body2" color="text.secondary">
                  None for this attribute
                </Typography>
              ),
          },
        ]}
        data={rows}
        rowsSelectable={false}
        isLoading={unmappedQuery.isLoading}
        topBarActions={(table) => [
          <Button
            key="export"
            startIcon={<FileDownload />}
            disabled={table.getFilteredRowModel().rows.length === 0}
            onClick={() => {
              // What the filters and sorting have left, rather than the page
              // being looked at: exporting ten of four hundred would be a
              // surprise to open.
              exportShown(table.getFilteredRowModel().rows.map((row) => row.original))
            }}
          >
            Export
          </Button>,
        ]}
        actions={[
          {
            action: Action.NEW,
            onAction: handleAddMapping,
            enabled: (row) => row.mapperUid !== null,
          },
        ]}
      />
    </SplitPanel>
  )
}
