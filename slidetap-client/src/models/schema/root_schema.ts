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

import { DatasetSchema } from './dataset_schema'
import {
  AnnotationSchema,
  ImageSchema,
  ObservationSchema,
  SampleSchema,
} from './item_schema'
import { ItemValueType } from '../item_value_type'
import { HierarchyLayout } from './hierarchy_layout'
import { ImagesLayout } from './images_layout'
import { ReviewUnitSchema } from './review_unit_schema'
import { OverviewLayout } from './overview_layout'
import { ProjectSchema } from './project_schema'

export interface RootSchema {
  readonly uid: string
  readonly name: string
  readonly project: ProjectSchema
  readonly dataset: DatasetSchema
  readonly samples: Record<string, SampleSchema>
  readonly images: Record<string, ImageSchema>
  readonly observations: Record<string, ObservationSchema>
  readonly annotations: Record<string, AnnotationSchema>
  readonly overviewLayouts: OverviewLayout[]
  readonly hierarchyLayouts: HierarchyLayout[]
  readonly imagesLayouts: ImagesLayout[]
  readonly reviewUnit: ReviewUnitSchema | null
}

/** Whether items of a schema are what a reviewer works through. */
export function isReviewUnit(rootSchema: RootSchema, schemaUid: string): boolean {
  return rootSchema.reviewUnit?.schemaUid === schemaUid
}

/** The schemas an item of this one can hang under. */
function parentSchemaUids(
  schema: SampleSchema | ImageSchema | ObservationSchema | AnnotationSchema,
): string[] {
  switch (schema.itemValueType) {
    case ItemValueType.SAMPLE:
      return (schema as SampleSchema).parents.map((relation) => relation.parentUid)
    case ItemValueType.IMAGE:
      return (schema as ImageSchema).samples.map((relation) => relation.sampleUid)
    case ItemValueType.ANNOTATION:
      return (schema as AnnotationSchema).images.map((relation) => relation.imageUid)
    case ItemValueType.OBSERVATION: {
      const observation = schema as ObservationSchema
      return [
        ...observation.samples.map((relation) => relation.sampleUid),
        ...observation.images.map((relation) => relation.imageUid),
        ...observation.annotations.map((relation) => relation.annotationUid),
      ]
    }
    default:
      return []
  }
}

/**
 * Whether the review unit answers for items of this schema — it, or anything
 * under it.
 *
 * What may be raised on: an issue is settled on the unit above the item, so
 * an item with none above it has nobody to answer for it.
 */
export function isUnderReviewUnit(rootSchema: RootSchema, schemaUid: string): boolean {
  const unitUid = rootSchema.reviewUnit?.schemaUid
  if (unitUid === undefined) {
    return false
  }
  const schemas: Record<
    string,
    SampleSchema | ImageSchema | ObservationSchema | AnnotationSchema
  > = {
    ...rootSchema.samples,
    ...rootSchema.images,
    ...rootSchema.observations,
    ...rootSchema.annotations,
  }
  const seen = new Set<string>()
  const walking = [schemaUid]
  while (walking.length > 0) {
    const uid = walking.pop() as string
    if (uid === unitUid) {
      return true
    }
    if (seen.has(uid)) {
      continue
    }
    seen.add(uid)
    const schema = schemas[uid]
    if (schema !== undefined) {
      walking.push(...parentSchemaUids(schema))
    }
  }
  return false
}
