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

/** How an item is exported otherwise than it is stored. */
export enum ExportNoticeKind {
  /** Exported as several items, such as a case as one case per specimen. */
  SPLIT = 'split',
  /** Exported as another item, with a pseudonym of its own. */
  REPLACED = 'replaced',
  /** Exported under another parent than stored, such as another case. */
  MOVED = 'moved',
  /** Exported under another pseudonym than stored. */
  RENAMED = 'renamed',
}

/** One thing to know about how an item is exported. */
export interface ExportNotice {
  kind: ExportNoticeKind
  message: string
}

/** What to know about how an item is exported, one notice for each way it is
 * exported otherwise than it is stored. */
export interface ExportNotices {
  notices: ExportNotice[]
}
