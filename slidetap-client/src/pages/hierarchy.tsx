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

import { Box, Typography } from '@mui/material'
import { type ReactElement } from 'react'
import { useParams } from 'react-router-dom'
import HierarchyView from 'src/components/hierarchy/hierarchy_view'
import ItemViewHeader from 'src/components/item/item_view_header'
import useItemStepping from 'src/components/item/use_item_stepping'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'
import { useQuery } from '@tanstack/react-query'

/** What hangs under one item, on its own rather than beside a review queue. */
export default function HierarchyPage(): ReactElement {
  const { projectUid, itemUid, hierarchyLayoutUid } = useParams()
  const rootSchema = useSchemaContext()
  const { pseudonymMode } = usePseudonym()
  const stepping = useItemStepping(
    itemUid ?? '',
    (uid) => `/project/${projectUid}/item/${uid}/hierarchy/${hierarchyLayoutUid}`,
  )
  const itemQuery = useQuery({
    queryKey: queryKeys.item.detail(itemUid ?? ''),
    queryFn: async () => await itemApi.get(itemUid ?? ''),
    enabled: itemUid !== undefined,
  })

  if (!projectUid || !itemUid || !hierarchyLayoutUid) {
    throw new Error('Project, Item, and Hierarchy Layout UIDs are required')
  }

  const layout = rootSchema.hierarchyLayouts.find(
    (candidate) => candidate.uid === hierarchyLayoutUid,
  )

  if (!layout) {
    return (
      <Box sx={{ p: 2 }}>
        <Typography>Hierarchy layout not found</Typography>
      </Box>
    )
  }

  return (
    // Fills the window rather than growing past it: the tree scrolls inside
    // itself, so its column headings stay where they are.
    <Box
      sx={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}
    >
      {itemQuery.data !== undefined && (
        <ItemViewHeader
          identifier={getDisplayIdentifier(itemQuery.data, pseudonymMode)}
          {...stepping}
        />
      )}
      <HierarchyView projectUid={projectUid} itemUid={itemUid} layout={layout} />
    </Box>
  )
}
