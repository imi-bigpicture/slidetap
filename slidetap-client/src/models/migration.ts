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

import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { ProjectStatus } from 'src/models/project_status'

/** Where the migration of a project is. */
export enum MigrationState {
  PLANNING = 'planning',
  CURATING = 'curating',
  COMPLETING = 'completing',
  FAILED = 'failed',
}

export enum MigrationObjectKind {
  PROJECT = 'project',
  DATASET = 'dataset',
  ITEM = 'item',
}

/** A top-level attribute of the target schema of an object that the
 * migration could not convert, and what the curator decided. */
export interface MigrationIssue {
  readonly uid: string
  /** The tag in the target schema. */
  readonly tag: string
  /** The attribute schema of the tag in the target root. */
  readonly attributeSchemaUid: string
  readonly displayName: string
  /** The attribute of the source object, null where it had none. */
  readonly original: Attribute<AttributeValueTypes> | null
  /** What could be converted, to start from. */
  readonly proposed: Attribute<AttributeValueTypes> | null
  readonly reason: string
  readonly decided: boolean
  readonly leftEmpty: boolean
  readonly decision: Attribute<AttributeValueTypes> | null
}

/** An attribute with a value that the migration left out, as it has no
 * target. */
export interface MigrationDroppedAttribute {
  readonly tag: string
  readonly displayName: string
  readonly displayValue: string | null
}

/** A project, dataset, or item with issues or dropped attributes. */
export interface MigrationObject {
  readonly uid: string
  readonly kind: MigrationObjectKind
  /** The name of the project or dataset, the identifier of an item. */
  readonly identifier: string
  /** The schema of the target root it is migrated to. */
  readonly schemaUid: string
  readonly schemaDisplayName: string
  readonly issues: MigrationIssue[]
  readonly dropped: MigrationDroppedAttribute[]
}

/** The migration of a project to another root schema, with its plan. */
export interface ProjectMigration {
  readonly projectUid: string
  readonly sourceRootSchemaUid: string
  readonly targetRootSchemaUid: string
  /** The name and version of the root migrated to. */
  readonly targetRootSchemaName: string
  readonly previousStatus: ProjectStatus
  readonly state: MigrationState
  /** Why planning or completing failed. */
  readonly error: string | null
  readonly created: string
  readonly updated: string
  readonly objects: MigrationObject[]
  readonly issues: number
  readonly decided: number
}
