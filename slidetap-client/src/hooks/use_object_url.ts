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

import { useCallback, useState, useSyncExternalStore } from 'react'

/** An object URL for a blob, made once per blob and revoked when the blob
 * changes or the component unmounts, so the blob is not held after it is no
 * longer shown. Undefined until the URL is made.
 *
 * The URL is made when the component subscribes to the blob, after render,
 * and revoked when it unsubscribes. A revoked URL is never the one rendered: a
 * component that subscribes again, as StrictMode has it do, is handed a fresh
 * one. Each component makes its own, so one that stops showing a blob never
 * revokes a URL another is still showing. */
export function useObjectUrl(blob: Blob | undefined): string | undefined {
  const [madeUrls] = useState(() => new Map<Blob, string>())
  const subscribe = useCallback(
    (onUrlChange: () => void) => {
      if (blob === undefined) {
        return () => {}
      }
      const url = URL.createObjectURL(blob)
      madeUrls.set(blob, url)
      onUrlChange()
      return () => {
        madeUrls.delete(blob)
        URL.revokeObjectURL(url)
      }
    },
    [blob, madeUrls],
  )
  return useSyncExternalStore(subscribe, () =>
    blob === undefined ? undefined : madeUrls.get(blob),
  )
}
