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


import { Cardinality } from 'src/models/schema/cardinality'

export interface ItemRelation {
  uid: string
  name: string
  description: string | null
}

export interface SampleToSampleRelation extends ItemRelation {
  parentTitle: string
  childTitle: string
  parentUid: string
  childUid: string
  /** How many parents of `parentUid` a child may have. */
  parents: Cardinality
  /** How many children of `childUid` a parent may have. */
  children: Cardinality
}

export interface ImageToSampleRelation extends ItemRelation {
  sampleTitle: string
  imageTitle: string
  imageUid: string
  sampleUid: string
  /** How many images a sample may have. */
  images: Cardinality
  /** How many samples an image may be of. */
  samples: Cardinality
  /** A holding place for images that could not be attached where they belong,
   * rather than a relation that describes the data. An image parked on one is
   * invalid until it is moved to the sample it is really of, and one left
   * empty is the normal case — nothing is required of it. */
  orphan: boolean
}

export interface AnnotationToImageRelation extends ItemRelation {
  annotationTitle: string
  imageTitle: string
  annotationUid: string
  imageUid: string
}

interface ObservationRelation extends ItemRelation {
  observationTitle: string
  observationUid: string
}

export interface ObservationToSampleRelation extends ObservationRelation {
  sampleTitle: string
  sampleUid: string
  }

export interface ObservationToImageRelation extends ObservationRelation {
  imageTitle: string
  imageUid: string
}

export interface ObservationToAnnotationRelation extends ObservationRelation {
  annotationTitle: string
  annotationUid: string
}
