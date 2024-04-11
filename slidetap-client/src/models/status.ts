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

export enum ImageStatus {
  NOT_STARTED = 1,
  DOWNLOADING = 2,
  DOWNLOADING_FAILED = 3,
  DOWNLOADED = 4,
  PRE_PROCESSING = 5,
  PRE_PROCESSING_FAILED = 6,
  PRE_PROCESSED = 7,
  POST_PROCESSING = 8,
  POST_PROCESSING_FAILED = 9,
  POST_PROCESSED = 10,
}

export const ImageStatusStrings = {
  [ImageStatus.NOT_STARTED]: 'Not started',
  [ImageStatus.DOWNLOADING]: 'Downloading',
  [ImageStatus.DOWNLOADING_FAILED]: 'Downloading failed',
  [ImageStatus.DOWNLOADED]: 'Downloaded',
  [ImageStatus.PRE_PROCESSING]: 'Pre-processing',
  [ImageStatus.PRE_PROCESSING_FAILED]: 'Pre-processing failed',
  [ImageStatus.PRE_PROCESSED]: 'Pre-processed',
  [ImageStatus.POST_PROCESSING]: 'Post-processing',
  [ImageStatus.POST_PROCESSING_FAILED]: 'Post-processing failed',
  [ImageStatus.POST_PROCESSED]: 'Post-processed',
}

export enum ProjectStatus {
  INITIALIZED = 1,
  METADATA_SEARCHING = 2,
  METADATA_SEARCH_COMPLETE = 3,
  IMAGE_PRE_PROCESSING = 4,
  IMAGE_PRE_PROCESSING_COMPLETE = 5,
  IMAGE_POST_PROCESSING = 6,
  IMAGE_POST_PROCESSING_COMPLETE = 7,
  EXPORTING = 8,
  EXPORT_COMPLETE = 9,
  FAILED = 10,
  DELETED = 11
}

export const ProjectStatusStrings = {
  [ProjectStatus.INITIALIZED]: 'Not started',
  [ProjectStatus.METADATA_SEARCHING]: 'Searching',
  [ProjectStatus.METADATA_SEARCH_COMPLETE]: 'Search complete',
  [ProjectStatus.IMAGE_PRE_PROCESSING]: 'Pre-processing',
  [ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE]: 'Pre-processed',
  [ProjectStatus.IMAGE_POST_PROCESSING]: 'Processing',
  [ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE]: 'Processed',
  [ProjectStatus.EXPORTING]: 'Exporting',
  [ProjectStatus.EXPORT_COMPLETE]: 'Exported',
  [ProjectStatus.FAILED]: 'Failed',
  [ProjectStatus.DELETED]: 'Deleted',
}

export enum ValueStatus {
  ORIGINAL_VALUE = 1,
  UPDATED_VALUE = 2,
  NO_MAPPABLE_VALUE = 3,
  NO_MAPPER = 4,
  NOT_MAPPED = 5,
  MAPPED = 6,
}
