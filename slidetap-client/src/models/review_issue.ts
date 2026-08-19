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

/** What raised an issue: what kind of thing, not which one. */
export enum ReviewIssueSource {
  User = 'user',
  MetadataImporter = 'metadata_importer',
  ImageImporter = 'image_importer',
  /** Raised because an item under the unit is not as valid as it is expected
   * to be, and settled when it becomes valid again. Nobody decides either
   * end of it, so it is shown as what is not valid rather than as something
   * raised. */
  Validation = 'validation',
}

/**
 * Something raised as wrong with an item, and where to settle it.
 *
 * Raised on any item and answered on the review unit above it: a block that
 * looks wrong is usually only decidable with the whole case in front of you.
 */
export interface ReviewIssue {
  readonly uid: string
  /** The item the issue is about. */
  readonly itemUid: string
  readonly itemIdentifier: string
  readonly itemSchemaUid: string
  /** The unit it is answered on, and the one that is flagged for it. */
  readonly reviewUnitUid: string
  readonly reason: string
  /** What kind of thing raised it. Which one is not recorded. */
  readonly source: ReviewIssueSource
  readonly raisedAt: string
  /** When it was settled, null while it is still open. */
  readonly resolvedAt: string | null
}
