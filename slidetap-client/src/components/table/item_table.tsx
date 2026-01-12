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
  Add,
  Delete,
  Done,
  PriorityHigh,
  Recycling,
  RestoreFromTrash,
  WarningTwoTone,
} from '@mui/icons-material'
import {
  Box,
  Chip,
  CircularProgress,
  IconButton,
  Paper,
  Popover,
  Stack,
  Tooltip,
  lighten,
} from '@mui/material'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
  MRT_Cell,
  MRT_ColumnDef,
  MRT_GlobalFilterTextField,
  MRT_ToggleFiltersButton,
  MaterialReactTable,
  useMaterialReactTable,
  type MRT_ColumnFiltersState,
  type MRT_PaginationState,
  type MRT_SortingState,
} from 'material-react-table'
import React, { useRef, useState } from 'react'
import { Action, ItemDetailAction } from 'src/models/action'
import { Batch } from 'src/models/batch'
import {
  isAnnotationItem,
  isAnnotationSchema,
  isImageItem,
  isImageSchema,
  isObservationItem,
  isSampleItem,
  isSampleSchema,
} from 'src/models/helpers'
import { Item } from 'src/models/item'
import { Project } from 'src/models/project'
import type { ItemSchema } from 'src/models/schema/item_schema'
import {
  RelationFilterType,
  SortType,
  type RelationFilter,
  type RelationFilterDefinition,
} from 'src/models/table_item'
import { Tag } from 'src/models/tag'
import itemApi from 'src/services/api/item_api'
import tagApi from 'src/services/api/tag_api'
import DisplayAttribute from '../attribute/display_attribute'
import DisplayItemIdentifiers from '../item/item_identifiers'
import RowActions from './row_actions'

interface ItemTableProps {
  project: Project
  batch?: Batch
  schema: ItemSchema
  rowsSelectable?: boolean
  actions?: {
    action: Action
    onAction: (item: Item, element: HTMLElement) => void
    enabled?: (item: Item) => boolean
    inMenu?: boolean
  }[]
  onRowsStateChange?: (itemUids: string[], state: boolean, element: HTMLElement) => void
  onRowView: (itemUid: string) => void
  onNew?: () => void
  refresh: boolean
}

export function ItemTable({
  project,
  batch,
  schema,
  rowsSelectable,
  actions,
  onRowsStateChange,
  onRowView,
  onNew,
  refresh,
}: ItemTableProps): React.ReactElement {
  const [columnFilters, setColumnFilters] = useState<MRT_ColumnFiltersState>([])
  const [sorting, setSorting] = useState<MRT_SortingState>([])
  const [pagination, setPagination] = useState<MRT_PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  })
  const [editingCell, setEditingCell] = useState<MRT_Cell<Item> | null>(null)
  const [displayRecycled, setDisplayRecycled] = useState(false)
  const [displayOnlyInValid, setDisplayOnlyInValid] = useState(false)
  const [detailComponent, setDetailComponent] = useState<React.ReactElement | null>(
    null,
  )
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailAnchorElement, setIdentifierDetailAnchorElement] =
    useState<HTMLElement | null>(null)
  const relationships: Record<string, RelationFilterDefinition> = {}
  if (isSampleSchema(schema)) {
    schema.children
      .filter((schema) => !schema.maxChildren || schema.maxChildren > 1)
      .forEach((schema) => {
        relationships[`relation.${schema.uid}.child.${schema.childUid}`] = {
          title: schema.childTitle,
          relationSchemaUid: schema.childUid,
          relationType: RelationFilterType.CHILD,
          valueGetter: (item: Item) =>
            isSampleItem(item) ? item.children?.[schema.childUid]?.length ?? 0 : 0,
        }
      })
    schema.parents
      .filter((schema) => !schema.maxParents || schema.maxParents > 1)
      .forEach((schema) => {
        relationships[`relation.${schema.uid}.parent.${schema.parentUid}`] = {
          title: schema.parentTitle,
          relationSchemaUid: schema.parentUid,
          relationType: RelationFilterType.PARENT,
          valueGetter: (item: Item) =>
            isSampleItem(item) ? item.parents?.[schema.parentUid]?.length ?? 0 : 0,
        }
      })
    schema.images.forEach((schema) => {
      relationships[`relation.${schema.uid}.image.${schema.imageUid}`] = {
        title: schema.imageTitle,
        relationSchemaUid: schema.imageUid,
        relationType: RelationFilterType.IMAGE,
        valueGetter: (item: Item) =>
          isSampleItem(item) ? item.images?.[schema.imageUid]?.length ?? 0 : 0,
      }
    })
    schema.observations.forEach((schema) => {
      relationships[`relation.${schema.uid}.observation.${schema.observationUid}`] = {
        title: schema.observationTitle,
        relationSchemaUid: schema.observationUid,
        relationType: RelationFilterType.OBSERVATION,
        valueGetter: (item: Item) =>
          isSampleItem(item)
            ? item.observations?.[schema.observationUid]?.length ?? 0
            : 0,
      }
    })
  } else if (isImageSchema(schema)) {
    schema.samples.forEach((schema) => {
      relationships[`relation.${schema.uid}.sample.${schema.sampleUid}`] = {
        title: schema.sampleTitle,
        relationSchemaUid: schema.sampleUid,
        relationType: RelationFilterType.SAMPLE,
        valueGetter: (item: Item) =>
          isImageItem(item) ? item.samples?.[schema.sampleUid]?.length ?? 0 : 0,
      }
    })
    schema.annotations.forEach((schema) => {
      relationships[`relation.${schema.uid}.annotation.${schema.annotationUid}`] = {
        title: schema.annotationTitle,
        relationSchemaUid: schema.annotationUid,
        relationType: RelationFilterType.ANNOTATION,
        valueGetter: (item: Item) =>
          isImageItem(item) ? item.annotations?.[schema.annotationUid]?.length ?? 0 : 0,
      }
    })
    schema.observations.forEach((schema) => {
      relationships[`relation.${schema.uid}.observation.${schema.observationUid}`] = {
        title: schema.observationTitle,
        relationSchemaUid: schema.observationUid,
        relationType: RelationFilterType.OBSERVATION,
        valueGetter: (item: Item) =>
          isImageItem(item)
            ? item.observations?.[schema.observationUid]?.length ?? 0
            : 0,
      }
    })
  } else if (isAnnotationSchema(schema)) {
    schema.observations.forEach((observationSchema) => {
      relationships[
        `relation.${observationSchema.uid}.observation.${observationSchema.observationUid}`
      ] = {
        title: observationSchema.observationTitle,
        relationSchemaUid: observationSchema.observationUid,
        relationType: RelationFilterType.OBSERVATION,
        valueGetter: (item: Item) =>
          isAnnotationItem(item)
            ? item.observations?.[observationSchema.observationUid]?.length ?? 0
            : 0,
      }
    })
  }

  const getItems = async (
    schemaUid: string,
    start: number,
    size: number,
    filters: MRT_ColumnFiltersState,
    sorting: MRT_SortingState,
    recycled?: boolean,
    invalid?: boolean,
  ): Promise<{ items: Item[]; count: number }> => {
    const tagFilters = filters.filter((filter) => filter.id === 'tags').pop()
      ?.value as string[]
    const identifierFilter = filters.find((filter) => filter.id === 'id')?.value as
      | string
      | null
    const attributeFilters = filters
      .filter((filter) => filter.id.startsWith('attributes.'))
      .reduce<Record<string, string>>(
        (filters, filter) => ({
          ...filters,
          [filter.id.split('attributes.')[1]]: String(filter.value),
        }),
        {},
      )
    const relationFilters = filters
      .filter((filter) => filter.id.startsWith('relation.'))
      .map((filter) => ({ filter: filter, definition: relationships[filter.id] }))
      .filter((filterObj) => filterObj.definition !== undefined)
      .reduce<RelationFilter[]>((filters, filterObj) => {
        const filterValue = filterObj.filter.value as [number | null, number | null]
        const minCount = filterValue[0] as number | undefined | null
        const maxCount = filterValue[1] as number | undefined | null
        if (
          (minCount === null || minCount === undefined) &&
          (maxCount === null || maxCount === undefined)
        ) {
          return filters
        }
        return [
          ...filters,
          {
            relationSchemaUid: filterObj.definition.relationSchemaUid,
            relationType: filterObj.definition.relationType,
            minCount: minCount === undefined ? null : minCount,
            maxCount: maxCount === undefined ? null : maxCount,
          },
        ]
      }, [])
    const sortingRequest = sorting.map((sort) => {
      if (sort.id === 'id') {
        return {
          sortType: SortType.IDENTIFIER,
          descending: sort.desc,
        }
      }
      if (sort.id === 'valid') {
        return { sortType: SortType.VALID, descending: sort.desc }
      }
      if (sort.id.startsWith('attributes')) {
        const column = sort.id.split('attributes.')[1]
        return {
          column: column,
          descending: sort.desc,
          sortType: SortType.ATTRIBUTE,
        }
      }
      if (sort.id.startsWith('relation.')) {
        const relation = relationships[sort.id]
        return {
          relationSchemaUid: relation.relationSchemaUid,
          relationType: relation.relationType,
          descending: sort.desc,
          sortType: SortType.RELATION,
        }
      }
      throw new Error(`Unknown sort type: ${sort.id}.`)
    })
    const request = {
      start,
      size,
      identifierFilter: identifierFilter,
      attributeFilters: attributeFilters,
      relationFilters: relationFilters,
      statusFilter: null,
      tagFilter: tagFilters,
      sorting: sortingRequest,
      included: recycled !== undefined ? !recycled : null,
      valid: invalid !== undefined ? !invalid : null,
    }
    return await itemApi.getItems<Item>(
      schemaUid,
      project.datasetUid,
      batch?.uid,
      request,
    )
  }
  const itemsQuery = useQuery({
    queryKey: [
      'items',
      schema.uid,
      columnFilters,
      sorting,
      pagination,
      displayRecycled,
      displayOnlyInValid,
    ],
    queryFn: async () => {
      return await getItems(
        schema.uid,
        pagination.pageIndex * pagination.pageSize,
        pagination.pageSize,
        columnFilters,
        sorting,
        displayRecycled,
        displayOnlyInValid ? true : undefined,
      )
    },
    refetchInterval: refresh ? 2000 : false,
    placeholderData: keepPreviousData,
  })
  const tagsQuery = useQuery({
    queryKey: ['tags'],
    queryFn: async () => {
      return await tagApi.getTags()
    },
  })

  const handleRowsState = (element: HTMLElement): void => {
    if (displayRecycled === undefined) {
      return
    }
    onRowsStateChange?.(
      table.getSelectedRowModel().flatRows.map((row) => row.id),
      displayRecycled,
      element,
    )
  }

  const handleNew = (): void => {
    onNew?.()
  }

  const columns: MRT_ColumnDef<Item>[] = [
    {
      id: 'id',
      header: 'Id',
      accessorKey: 'identifier',
      size: 0,
      Cell: ({ row, cell }) => {
        const cellReference = useRef(null)
        const item = row.original
        const value = cell.getValue<string>()
        return (
          <Chip
            ref={cellReference}
            onClick={(event) => {
              setDetailComponent(
                <DisplayItemIdentifiers
                  item={item}
                  action={ItemDetailAction.VIEW}
                  direction="column"
                  handleIdentifierUpdate={() => {}}
                  handleNameUpdate={() => {}}
                  handleCommentUpdate={() => {}}
                />,
              )
              setIdentifierDetailAnchorElement(event.currentTarget)
              setDetailOpen(true)
            }}
            label={value}
          />
        )
      },
    },
    {
      id: 'valid',
      header: 'Valid',
      accessorKey: 'valid',
      enableColumnFilter: false,
      enableSorting: false,
      size: 0,
      Cell: ({ cell }) =>
        cell.getValue<boolean>() ? (
          <Done color="success" />
        ) : (
          <PriorityHigh color="warning" />
        ),
    },
    ...Object.values(schema.attributes)
      .filter((attributeSchema) => attributeSchema.displayInTable)
      .map((attributeSchema) => {
        return {
          id: `attributes.${attributeSchema.tag}`,
          header: attributeSchema.displayName,
          accessorKey: `attributes.${attributeSchema.tag}.displayValue`,
          size: 0,

          Cell: ({ row }: { row: MRT_Cell<Item>['row'] }) => {
            const cellReference = useRef(null)
            const item = row.original
            const attribute = item.attributes[attributeSchema.tag]
            if (attribute === undefined) {
              return null
            }
            return (
              <Chip
                ref={cellReference}
                onClick={() => {
                  setDetailComponent(
                    <Box sx={{ p: 1 }}>
                      <DisplayAttribute
                        attribute={attribute}
                        schema={attributeSchema}
                        action={ItemDetailAction.VIEW}
                        displayAsRoot={true}
                        handleAttributeOpen={() => {}}
                        handleAttributeUpdate={() => {}}
                      />
                    </Box>,
                  )
                  setIdentifierDetailAnchorElement(cellReference.current)
                  setDetailOpen(true)
                }}
                label={attribute.displayValue}
              />
            )
          },
        }
      }),
    {
      id: 'tags',
      header: 'Tags',
      accessorKey: 'tags',
      size: 0,
      Cell: ({ cell }) => {
        const tagUids = cell.getValue() as string[] | undefined
        if (!tagUids) return null
        return tagUids
          .map((uid) =>
            tagsQuery.data ? tagsQuery.data.find((tag) => tag.uid === uid) : undefined,
          )
          .filter((tag): tag is Tag => tag !== undefined)
          .map((tag) => (
            <Tooltip key={tag.uid} title={tag.description ?? undefined}>
              <Chip
                label={tag.name}
                style={tag.color ? { backgroundColor: tag.color } : undefined}
              />
            </Tooltip>
          ))
      },
      filterVariant: 'multi-select' as const,
    },
  ]
  Object.entries(relationships).forEach((relation) => {
    const [id, definition] = relation
    columns.push({
      id: id,
      header: definition.title,
      accessorFn: (row) => row,
      filterVariant: 'range' as const,
      size: 0,

      Cell: ({ row }) => {
        const cellReference = useRef(null)
        const item = row.original
        const value = definition.valueGetter(item)
        return (
          <Chip
            ref={cellReference}
            disabled={value === 0}
            onClick={() => {
              if (value === 0) {
                return
              }
              setDetailComponent(
                <ItemRelations
                  relation={definition}
                  item={row.original}
                  onClick={onRowView}
                />,
              )
              setIdentifierDetailAnchorElement(cellReference.current)
              setDetailOpen(true)
            }}
            label={value}
          />
        )
      },
    })
  })

  const table = useMaterialReactTable({
    columns,
    data: itemsQuery.data?.items ?? [],
    state: {
      isLoading: itemsQuery.isLoading,
      showAlertBanner: itemsQuery.isError,
      showProgressBars: itemsQuery.isFetching,
      sorting,
      columnFilters,
      pagination,
      editingCell,
    },
    initialState: { density: 'compact' },
    manualFiltering: true,
    manualPagination: true,
    manualSorting: true,
    onEditingCellChange: setEditingCell,
    onColumnFiltersChange: setColumnFilters,
    onPaginationChange: setPagination,
    onSortingChange: setSorting,
    rowCount: itemsQuery.data?.count ?? 0,
    enableRowSelection: rowsSelectable,
    enableRowActions: true,
    positionActionsColumn: 'last',
    enableEditing: true,
    editDisplayMode: 'custom',
    renderRowActions: ({ row }) => {
      return <RowActions row={row} actions={actions} displayRestore={displayRecycled} />
    },
    getRowId: (originalRow) => originalRow.uid,
    muiToolbarAlertBannerProps: itemsQuery.isError
      ? {
          color: 'error',
          children: 'Error loading data',
        }
      : undefined,
    muiTableBodyCellProps: ({ cell, column, table }) => ({
      onClick: () => {
        table.setEditingCell(cell) //set editing cell
        //optionally, focus the text field
        queueMicrotask(() => {
          const textField = table.refs.editInputRefs.current?.[column.id]
          if (textField) {
            textField.focus()
            textField.select?.()
          }
        })
      },
    }),
    renderTopToolbar: ({ table }) => {
      return (
        <Box
          sx={(theme) => ({
            backgroundColor: lighten(theme.palette.background.default, 0.05),
            display: 'flex',
            gap: '0.5rem',
            p: '8px',
            justifyContent: 'space-between',
          })}
        >
          <Box>
            <Tooltip title="Toggle display of deleted items">
              <IconButton
                onClick={() => {
                  setDisplayOnlyInValid(false)
                  setDisplayRecycled(!displayRecycled)
                }}
                color={displayRecycled ? 'primary' : 'default'}
              >
                <Recycling />
              </IconButton>
            </Tooltip>
            <Tooltip title="Toggle display of invalid items">
              <IconButton
                onClick={() => {
                  setDisplayRecycled(false)
                  setDisplayOnlyInValid(!displayOnlyInValid)
                }}
                color={displayOnlyInValid ? 'primary' : 'default'}
              >
                <WarningTwoTone />
              </IconButton>
            </Tooltip>
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <MRT_GlobalFilterTextField table={table} />
            <MRT_ToggleFiltersButton table={table} />
          </Box>
          <Box sx={{ display: 'flex', gap: '0.5rem' }}>
            {displayRecycled !== undefined && handleRowsState !== undefined && (
              <IconButton
                disabled={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                }
                onClick={(event) => handleRowsState(event.currentTarget)}
                color={
                  !table.getIsSomeRowsSelected() && !table.getIsAllRowsSelected()
                    ? 'default'
                    : 'primary'
                }
              >
                {displayRecycled ? <RestoreFromTrash /> : <Delete />}
              </IconButton>
            )}

            {onNew !== undefined && (
              <IconButton
                disabled={
                  !displayRecycled &&
                  (table.getIsSomeRowsSelected() || table.getIsAllRowsSelected())
                }
                onClick={handleNew}
                color={
                  !displayRecycled &&
                  (table.getIsSomeRowsSelected() || table.getIsAllRowsSelected())
                    ? 'default'
                    : 'primary'
                }
              >
                <Add />
              </IconButton>
            )}
          </Box>
        </Box>
      )
    },
  })
  return (
    <React.Fragment>
      <MaterialReactTable table={table} />
      <Popover
        open={detailOpen}
        anchorEl={detailAnchorElement}
        onClose={() => {
          setDetailOpen(false)
          setIdentifierDetailAnchorElement(null)
        }}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center',
        }}
        transformOrigin={{
          vertical: -10,
          horizontal: 'center',
        }}
      >
        <Paper sx={{ p: 1 }} style={{ maxWidth: '300px' }}>
          {detailComponent}
        </Paper>
      </Popover>
    </React.Fragment>
  )
}

interface ItemRelationProps {
  itemUid: string
  onClick: (itemUid: string) => void
}

function ItemRelation({ itemUid, onClick }: ItemRelationProps): React.ReactElement {
  const itemQuery = useQuery({
    queryKey: ['item', itemUid],
    queryFn: async () => {
      return await itemApi.get(itemUid)
    },
  })
  if (itemQuery.isLoading) {
    return <CircularProgress />
  }
  if (itemQuery.data === undefined) {
    return <></>
  }
  return (
    <Chip
      label={itemQuery.data.identifier}
      onClick={() => onClick(itemQuery.data.uid)}
    />
  )
}

interface ItemRelationsProps {
  relation: RelationFilterDefinition
  item: Item
  onClick: (itemUid: string) => void
}

function ItemRelations({
  relation,
  item,
  onClick,
}: ItemRelationsProps): React.ReactElement {
  const getRelationItemUids = (item: Item): string[] => {
    if (isSampleItem(item)) {
      if (relation.relationType === RelationFilterType.CHILD) {
        return item.children[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.PARENT) {
        return item.parents[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.IMAGE) {
        return item.images[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.OBSERVATION) {
        return item.observations[relation.relationSchemaUid]
      }
    }
    if (isImageItem(item)) {
      if (relation.relationType === RelationFilterType.SAMPLE) {
        return item.samples[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.ANNOTATION) {
        return item.annotations[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.OBSERVATION) {
        return item.observations[relation.relationSchemaUid]
      }
    }
    if (isAnnotationItem(item)) {
      if (relation.relationType === RelationFilterType.OBSERVATION) {
        return item.observations[relation.relationSchemaUid]
      }
      if (relation.relationType === RelationFilterType.IMAGE) {
        if (item.image !== null && item.image[0] === relation.relationSchemaUid) {
          return [item.image[1]]
        }
      }
    }
    if (isObservationItem(item)) {
      if (relation.relationType === RelationFilterType.IMAGE) {
        if (item.image !== null && item.image[0] === relation.relationSchemaUid) {
          return [item.image[1]]
        }
      }
      if (relation.relationType === RelationFilterType.SAMPLE) {
        if (item.sample !== null && item.sample[0] === relation.relationSchemaUid) {
          return [item.sample[1]]
        }
      }
      if (relation.relationType === RelationFilterType.ANNOTATION) {
        if (
          item.annotation !== null &&
          item.annotation[0] === relation.relationSchemaUid
        ) {
          return [item.annotation[1]]
        }
      }
    }
    throw new Error(`Unknown relation type: ${relation.relationType}.`)
  }
  const relationItemUids = getRelationItemUids(item)
  return (
    <Stack spacing={1} direction={'column'}>
      {relationItemUids.map((uid) => (
        <ItemRelation key={uid} itemUid={uid} onClick={onClick} />
      ))}
    </Stack>
  )
}
