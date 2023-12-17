export enum ImageStatus {
  NOT_STARTED = 1,
  DOWNLOADING = 2,
  DOWNLOADED = 3,
  PRE_PROCESSING = 4,
  PRE_PROCESSED = 5,
  POST_PROCESSING = 6,
  POST_PROCESSED = 7,
  FAILED = 8,
  COMPLETED = 9
}

export const ImageStatusStrings = {
  [ImageStatus.NOT_STARTED]: 'Not started',
  [ImageStatus.DOWNLOADING]: 'Downloading',
  [ImageStatus.DOWNLOADED]: 'Downloaded',
  [ImageStatus.PRE_PROCESSING]: 'Pre-processing',
  [ImageStatus.PRE_PROCESSED]: 'Pre-processed',
  [ImageStatus.POST_PROCESSING]: 'Post-processing',
  [ImageStatus.POST_PROCESSED]: 'Post-processed',
  [ImageStatus.FAILED]: 'Failed',
  [ImageStatus.COMPLETED]: 'Completed',
}

export enum ProjectStatus {
  INITIALIZED = 1,
  METADATA_SEARCHING = 2,
  METEDATA_SEARCH_COMPLETE = 3,
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
  [ProjectStatus.METEDATA_SEARCH_COMPLETE]: 'Search complete',
  [ProjectStatus.IMAGE_PRE_PROCESSING]: 'Downloading',
  [ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE]: 'Downloaded',
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
