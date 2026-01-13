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

/**
 * Centralized query key factory for React Query.
 *
 * This factory provides consistent, type-safe query keys across the application.
 * Using a factory pattern ensures:
 * - Consistent key structure
 * - Type safety
 * - Easier cache invalidation
 * - Better autocomplete support
 *
 * @example
 * // In a component
 * const projectQuery = useQuery({
 *   queryKey: queryKeys.project.detail(projectUid),
 *   queryFn: () => projectApi.get(projectUid)
 * })
 *
 * // Invalidate all projects
 * queryClient.invalidateQueries({ queryKey: queryKeys.project.all })
 *
 * // Invalidate specific project
 * queryClient.invalidateQueries({ queryKey: queryKeys.project.detail(projectUid) })
 */

import { MRT_ColumnFiltersState, MRT_SortingState } from 'material-react-table'
import type { BatchStatus } from 'src/models/batch_status'
import type { ProjectStatus } from 'src/models/project_status'
import { Size } from 'src/models/setting'
import { RelationFilterDefinition } from 'src/models/table_item'

export const queryKeys = {
  // Projects
  project: {
    all: ['projects'] as const,
    lists: () => [...queryKeys.project.all, 'list'] as const,
    list: (filters?: { status?: ProjectStatus }) =>
      [...queryKeys.project.lists(), filters] as const,
    details: () => [...queryKeys.project.all, 'detail'] as const,
    detail: (projectUid: string) =>
      [...queryKeys.project.details(), projectUid] as const,
    validation: (projectUid: string) =>
      [...queryKeys.project.detail(projectUid), 'validation'] as const,
  },

  // Batches
  batch: {
    all: ['batches'] as const,
    lists: () => [...queryKeys.batch.all, 'list'] as const,
    list: (projectUid: string, filters?: { status?: BatchStatus }) =>
      [...queryKeys.batch.lists(), projectUid, filters] as const,
    details: () => [...queryKeys.batch.all, 'detail'] as const,
    detail: (batchUid: string) =>
      [...queryKeys.batch.details(), batchUid] as const,
    validation: (batchUid: string) =>
      [...queryKeys.batch.detail(batchUid), 'validation'] as const,
  },

  // Datasets
  dataset: {
    all: ['datasets'] as const,
    details: () => [...queryKeys.dataset.all, 'detail'] as const,
    detail: (datasetUid: string) =>
      [...queryKeys.dataset.details(), datasetUid] as const,
  },

  // Items
  item: {
    all: ['items'] as const,
    lists: () => [...queryKeys.item.all, 'list'] as const,
    list: (schemaUid: string, datasetUid: string | null = null, batchUid: string | null = null) =>
      [...queryKeys.item.lists(), schemaUid, { datasetUid, batchUid }] as const,
    details: () => [...queryKeys.item.all, 'detail'] as const,
    detail: (itemUid: string) =>
      [...queryKeys.item.details(), itemUid] as const,
    references: (schemaUid: string, datasetUid: string, batchUid: string | null) =>
      [...queryKeys.item.all, 'references', schemaUid, datasetUid, batchUid] as const,
    preview: (itemUid: string) =>
      [...queryKeys.item.detail(itemUid), 'preview'] as const,
    images: (itemUid: string, groupBySchemaUid: string, imageSchemaUid: string | null = null) =>
      [...queryKeys.item.detail(itemUid), 'images', groupBySchemaUid, imageSchemaUid] as const,
      table: (schemaUid: string, datasetUid: string, batchUid: string | null = null, relationships: Record<string, RelationFilterDefinition>, start: number, size: number, columnFilters: MRT_ColumnFiltersState, sorting: MRT_SortingState) => [...queryKeys.item.all, 'table', schemaUid, { datasetUid, batchUid }, relationships, start, size, columnFilters, sorting] as const,

  },

  // Images
  image: {
    all: ['images'] as const,
    lists: () => [...queryKeys.image.all, 'list'] as const,
    list: (schemaUid: string, datasetUid: string | null = null, batchUid: string | null = null) =>
      [...queryKeys.image.lists(), schemaUid, { datasetUid, batchUid }] as const,
    thumbnail: (imageUid: string, size: Size) => [...queryKeys.image.all, 'thumbnail', imageUid, size] as const,
    withThumbnails: (datasetUid: string | null = null, batchUid: string | null = null) => [...queryKeys.image.all, 'withThumbnails', { datasetUid, batchUid }] as const,
    dzi: (imageUid: string) => [...queryKeys.image.all, 'dzi', imageUid] as const,
    forItem: (itemUid: string, groupBySchemaUid: string) => [...queryKeys.image.all, 'forItem', itemUid, groupBySchemaUid] as const,
  },

  // Schemas
  schema: {
    all: ['schemas'] as const,
    root: () => [...queryKeys.schema.all, 'root'] as const,
    items: () => [...queryKeys.schema.all, 'items'] as const,
    item: (schemaUid: string) =>
      [...queryKeys.schema.items(), schemaUid] as const,
    attributes: () => [...queryKeys.schema.all, 'attributes'] as const,
    attribute: (schemaUid: string) =>
      [...queryKeys.schema.attributes(), schemaUid] as const,
    hierarchy: (schemaUid: string) => [...queryKeys.schema.all, 'hierarchy', schemaUid] as const,
  },

  // Mappers
  mapper: {
    all: ['mappers'] as const,
    lists: () => [...queryKeys.mapper.all, 'list'] as const,
    list: () => [...queryKeys.mapper.lists()] as const,
    details: () => [...queryKeys.mapper.all, 'detail'] as const,
    detail: (mapperUid: string) =>
      [...queryKeys.mapper.details(), mapperUid] as const,
    mappings: (mapperUid: string) =>
      [...queryKeys.mapper.detail(mapperUid), 'mappings'] as const,
    attributes: (mapperUid: string) =>
      [...queryKeys.mapper.detail(mapperUid), 'attributes'] as const,
    unmappedAttributes: (mapperUid: string) =>
      [...queryKeys.mapper.detail(mapperUid), 'unmapped'] as const,
    mapping: (mappingUid: string) =>
      [...queryKeys.mapper.all, 'mapping', mappingUid] as const,

  },

  // Mappings
  mapping: {
    all: ['mappings'] as const,
    details: () => [...queryKeys.mapping.all, 'detail'] as const,
    detail: (mappingUid: string) =>
      [...queryKeys.mapping.details(), mappingUid] as const,
  },

  // Mapper Groups
  mapperGroup: {
    all: ['mapperGroups'] as const,
    details: () => [...queryKeys.mapperGroup.all, 'detail'] as const,
    detail: (groupUid: string) =>
      [...queryKeys.mapperGroup.details(), groupUid] as const,
  },

  // Attributes
  attribute: {
    all: ['attributes'] as const,
    details: () => [...queryKeys.attribute.all, 'detail'] as const,
    detail: (attributeUid: string) =>
      [...queryKeys.attribute.details(), attributeUid] as const,

  },

  // Tags
  tag: {
    all: ['tags'] as const,
    lists: () => [...queryKeys.tag.all, 'list'] as const,
    list: () => [...queryKeys.tag.lists()] as const,
  },

  // Session
  session: {
    all: ['session'] as const,
    status: () => [...queryKeys.session.all, 'status'] as const,
  },
} as const

/**
 * Helper type to extract the return type of a query key function.
 * Useful for type-safe query key comparisons.
 *
 * @example
 * type ProjectDetailKey = QueryKey<typeof queryKeys.project.detail>
 */
export type QueryKey<T extends (...args: unknown[]) => readonly unknown[]> = ReturnType<T>
