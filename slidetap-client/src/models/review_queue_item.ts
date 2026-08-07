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

import { ReviewStatus } from 'src/models/review_status'

/**
 * One entry in the list a reviewer works through.
 *
 * Carries the status and the reason so the list can say where each entry
 * stands and what it was flagged for without reading every item in full.
 */
export interface ReviewQueueItem {
  uid: string
  identifier: string
  pseudonym: string | null
  reviewStatus: ReviewStatus
  reviewReason: string | null
  /** When a user last saved the item, as an ISO string. Null for one nobody
   * has edited — an import is not a save. */
  lastSaved: string | null
}
