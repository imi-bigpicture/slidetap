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
 * Which batch an address is of.
 *
 * On the address rather than held beside it, so that reloading a view of a
 * batch comes back to that batch rather than to the first of the project.
 *
 * Only where the view is a batch's, though: the project's own views — its
 * settings, its dataset, the whole dataset curated or reviewed — are of no
 * batch, and naming one on their address would say something that is not true
 * of them. The bar carries the batch across those views itself.
 *
 * Two params say it, for the two kinds of view that are a batch's. A batch
 * view is named by `batch`, since the batch is what the view is. An item view
 * is named by `batchUid`, which is also how far it steps and what it counts,
 * so that an item opened from a batch is read as that batch's throughout.
 *
 * Where no address names one — the project's own views — the bar falls back to
 * what it was last on, which is remembered per tab so that reloading one of
 * those views does not send it back to the first batch of the project. The
 * address still wins wherever it says anything.
 */
export const SELECTED_BATCH_PARAM = 'batch'
const VIEW_BATCH_PARAM = 'batchUid'

const REMEMBERED_BATCH_KEY = 'slidetap.selectedBatch'

/** The batch the bar was last on in this project, for the views whose address
 * says nothing about one. Per tab, so that two projects open side by side do
 * not move each other's bar. */
export function readRememberedBatch(projectUid: string): string | undefined {
  try {
    return (
      sessionStorage.getItem(`${REMEMBERED_BATCH_KEY}.${projectUid}`) ?? undefined
    )
  } catch {
    // Storage the browser will not hand out is a bar that forgets, not a view
    // that fails to open.
    return undefined
  }
}

export function rememberBatch(projectUid: string, batchUid: string): void {
  try {
    sessionStorage.setItem(`${REMEMBERED_BATCH_KEY}.${projectUid}`, batchUid)
  } catch {
    // As above.
  }
}

/** The batch an address is of, however it names it. */
export function readAddressedBatch(
  searchParams: URLSearchParams,
): string | undefined {
  return (
    searchParams.get(SELECTED_BATCH_PARAM) ??
    searchParams.get(VIEW_BATCH_PARAM) ??
    undefined
  )
}

/**
 * `target` with the batch it is of written into it, or with it taken off where
 * there is none.
 *
 * Whatever it said before is replaced: an address remembered from before the
 * bar was moved to another batch would otherwise take it back to the old one.
 * `target` may carry a query of its own, which is kept.
 */
export function withSelectedBatch(
  target: string,
  batchUid: string | undefined,
): string {
  const [path, search] = target.split('?')
  const params = new URLSearchParams(search)
  if (batchUid === undefined) {
    params.delete(SELECTED_BATCH_PARAM)
  } else {
    params.set(SELECTED_BATCH_PARAM, batchUid)
  }
  const query = params.toString()
  return query.length > 0 ? `${path}?${query}` : path
}
