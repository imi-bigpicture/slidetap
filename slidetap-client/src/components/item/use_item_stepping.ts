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

import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'

/** What the header needs to step from one item to the next. */
export interface ItemStepping {
  onPrevious: () => void
  onNext: () => void
  hasPrevious: boolean
  hasNext: boolean
}

/**
 * Stepping through the items of the same kind, staying in the view being read.
 *
 * A page of one item is opened to work through several — the next case, the
 * next slide — so the arrows go to the same view of the neighbour rather than
 * back to a list. Which item is next is the order the items are named in, which
 * is the order every list of them is read in.
 *
 * `addressOf` builds the address of the view for an item: the same route with
 * the neighbour in place of the item.
 */
export default function useItemStepping(
  itemUid: string,
  addressOf: (itemUid: string) => string,
): ItemStepping {
  const navigate = useNavigate()
  const { pseudonymMode } = usePseudonym()
  const neighboursQuery = useQuery({
    queryKey: queryKeys.item.neighbours(itemUid, pseudonymMode),
    queryFn: async () => await itemApi.getNeighbours(itemUid, pseudonymMode),
    // Called before the caller has checked its route parameters, so it can be
    // handed nothing at all.
    enabled: itemUid !== '',
  })
  const previousUid = neighboursQuery.data?.previousUid ?? null
  const nextUid = neighboursQuery.data?.nextUid ?? null
  return {
    onPrevious: () => {
      if (previousUid !== null) {
        navigate(addressOf(previousUid))
      }
    },
    onNext: () => {
      if (nextUid !== null) {
        navigate(addressOf(nextUid))
      }
    },
    hasPrevious: previousUid !== null,
    hasNext: nextUid !== null,
  }
}
