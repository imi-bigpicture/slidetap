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

/** What a project can be offered: whether its root schema is editable,
 * with the project's state applied. Viewing, validating, and deleting a
 * project are offered for every project on a provided root; a project that
 * cannot be edited is view only. */
export interface ProjectActions {
  /** Every change to the project: editing, search, images, pseudonyms,
   * preview, and export. */
  readonly edit: boolean
  /** Whether a migration is available from the project's root to the root of
   * new projects, whether or not the project can be migrated now. */
  readonly migrationAvailable: boolean
  /** Why the project cannot be converted now, null where it can or where its
   * root has no migration. */
  readonly migrateRefusal: string | null
}
