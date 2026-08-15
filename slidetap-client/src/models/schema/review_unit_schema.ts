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

import { MetadataImportCompleteness } from './metadata_import_completeness'
import { ReviewLayout } from './review_layout'

/** The item schema that is reviewed. */
export interface ReviewUnitSchema {
  /** The item schema whose items are reviewed. */
  schemaUid: string
  /** What the reviewer is shown of one, tab by tab. */
  layout: ReviewLayout
  /** What to exclude when validating the unit and the items under it, while
   * the batch is still being imported. Acted on by the server. */
  completeness: MetadataImportCompleteness | null
}
