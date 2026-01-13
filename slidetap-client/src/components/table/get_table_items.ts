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
    type MRT_ColumnFiltersState,
    type MRT_SortingState
} from 'material-react-table'
import { Batch } from 'src/models/batch'
import { Item } from 'src/models/item'
import {
    RelationFilter,
    RelationFilterDefinition,
    SortType
} from 'src/models/table_item'
import itemApi from 'src/services/api/item_api'

export const getItems = async <T extends Item>(
    schemaUid: string,
    datasetUid: string,
    batch: Batch | null,
    relationships: Record<string, RelationFilterDefinition>,
    start: number,
    size: number,
    filters: MRT_ColumnFiltersState,
    sorting: MRT_SortingState,
    recycled?: boolean,
    invalid?: boolean,
): Promise<{ items: T[]; count: number } > => {
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
    const statusFilter = filters.find((filter) => filter.id === 'status')?.value
        ? (filters.find((filter) => filter.id === 'status')?.value as string[]).map(
                (status) => parseInt(status),
            )
        : null
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
        if (sort.id == 'status') {
            return {
                sortType: SortType.STATUS,
                descending: sort.desc,
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
        statusFilter: statusFilter,
        tagFilter: tagFilters,
        sorting: sortingRequest,
        included: recycled !== undefined ? !recycled : null,
        valid: invalid !== undefined ? !invalid : null,
    }
    return await itemApi.getItems<T>(schemaUid, datasetUid, batch?.uid, request)
}