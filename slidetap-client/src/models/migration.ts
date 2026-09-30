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

/** What migrating a project does to the attributes of one attribute schema. */
export interface MigrationAttributeChange {
  readonly attributeSchemaUid: string
  readonly tag: string
  readonly displayName: string
  /** Attributes with a value that the conversion left out. */
  readonly dropped: number
  /** Attributes not valid after the conversion, a required one without a
   * value included. */
  readonly invalid: number
}

/** What migrating a project to another root schema would do. */
export interface MigrationReport {
  readonly projectUid: string
  readonly sourceRootSchemaUid: string
  readonly targetRootSchemaUid: string
  /** The name and version of the root migrated to. */
  readonly targetRootSchemaName: string
  readonly items: number
  readonly attributes: MigrationAttributeChange[]
}
