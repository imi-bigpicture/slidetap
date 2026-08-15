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

import {
  Box,
  LinearProgress,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import { type ReactElement } from 'react'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'

interface NonValidItemsProps {
  itemUid: string
  /** The item the panel beside this one is showing, if any. */
  openedItemUid: string
  /** Show an item beside the list. The rest of the list goes with it, so that
   * stepping on from one goes to the next thing to fix. */
  onOpenItem: (itemUid: string, siblingUids: string[]) => void
}

/**
 * What is wrong under the item being reviewed, as a list to work through.
 *
 * Every kind of item at once, named by schema, so that a reviewer can reach
 * what the flag refers to whether or not another panel happens to show that
 * kind. What is wrong with one is not said here — the link opens the item,
 * which says it.
 */
export default function NonValidItems({
  itemUid,
  openedItemUid,
  onOpenItem,
}: NonValidItemsProps): ReactElement {
  const rootSchema = useSchemaContext()
  const nonValidQuery = useQuery({
    queryKey: queryKeys.item.nonValidItems(itemUid),
    queryFn: async () => await itemApi.getReviewUnitNonValidItems(itemUid),
  })

  const schemaName = (schemaUid: string): string => {
    const schema =
      rootSchema.samples[schemaUid] ??
      rootSchema.images[schemaUid] ??
      rootSchema.observations[schemaUid] ??
      rootSchema.annotations[schemaUid]
    return schema?.displayName ?? 'Item'
  }

  if (nonValidQuery.isLoading) {
    return <LinearProgress />
  }
  const items = nonValidQuery.data ?? []
  if (items.length === 0) {
    return <Typography sx={{ p: 2 }}>Nothing here is waiting on anything.</Typography>
  }
  return (
    <Box sx={{ height: '100%', overflowY: 'auto' }}>
      <List dense>
        {items.map((item) => (
          <ListItem key={item.uid} divider disablePadding>
            <ListItemButton
              selected={item.uid === openedItemUid}
              onClick={() =>
                onOpenItem(
                  item.uid,
                  items.map((other) => other.uid),
                )
              }
            >
              <ListItemText
                primary={item.identifier}
                secondary={schemaName(item.schemaUid)}
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  )
}
