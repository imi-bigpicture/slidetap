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
export enum MigrationStatus {
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

/** A top-level attribute of an object that the migration could not convert,
 * left invalid, or dropped, and how the curator resolved it. */
export interface AttributeMigrationIssue {
  readonly uid: string
  /** The tag in the target schema, or in the source schema for a dropped
   * attribute. */
  readonly tag: string
  /** The attribute schema of the tag in the target root, null for a dropped
   * attribute. */
  readonly targetAttributeSchemaUid: string | null
  /** The display name of the target attribute, or of the source attribute for
   * a dropped attribute. */
  readonly displayName: string
  /** The attribute of the source object, null where it had none. */
  readonly original: Attribute<AttributeValueTypes> | null
  /** What could be converted, to start from. */
  readonly proposed: Attribute<AttributeValueTypes> | null
  /** What needs the curator's decision: a value the migration could not
   * migrate, an attribute the migration made invalid, or an attribute it
   * dropped. */
  readonly problem: string
  /** When the issue was resolved, or the dropped attribute accepted, null until
   * it is. */
  readonly resolvedAt: string | null
  /** The value the issue is resolved with, null where left empty, accepted as
   * dropped, or not yet resolved. */
  readonly resolved: Attribute<AttributeValueTypes> | null
}

/** A project, dataset, or item with attribute issues. */
export interface ObjectMigrationIssues {
  readonly uid: string
  readonly kind: MigrationObjectKind
  /** The name of the project or dataset, the identifier of an item. */
  readonly identifier: string
  /** The schema of the target root it is migrated to. */
  readonly targetSchemaUid: string
  readonly targetSchemaDisplayName: string
  /** The attribute issues, the dropped attributes included. */
  readonly attributeIssues: AttributeMigrationIssue[]
}

/** The migration of a project to another root schema, with its plan. */
export interface ProjectMigration {
  readonly projectUid: string
  readonly sourceRootSchemaUid: string
  readonly targetRootSchemaUid: string
  /** The name and version of the root migrated to. */
  readonly targetRootSchemaName: string
  readonly previousProjectStatus: ProjectStatus
  readonly status: MigrationStatus
  /** Why planning or completing failed. */
  readonly error: string | null
  readonly created: string
  readonly updated: string
  /** The issues of each object that has any: the project, the dataset, then
   * the items by identifier. */
  readonly issues: ObjectMigrationIssues[]
}
