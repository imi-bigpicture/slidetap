export enum ImageStatus {
  NOT_STARTED = 1,
  DOWNLOADING = 2,
  PROCESSING = 3,
  FAILED = 4,
  COMPLETED = 5,
}

export const ImageStatusStrings = {
  [ImageStatus.NOT_STARTED]: 'Not started',
  [ImageStatus.DOWNLOADING]: 'Downloading',
  [ImageStatus.PROCESSING]: 'Processing',
  [ImageStatus.FAILED]: 'Failed',
  [ImageStatus.COMPLETED]: 'Completed',
}

export enum ProjectStatus {
  NOT_STARTED = 1,
  SEARCHING = 2,
  SEARCH_COMPLETE = 3,
  STARTED = 4,
  FAILED = 5,
  COMPLETED = 6,
  SUMBITTED = 7,
}

export const ProjectStatusStrings = {
  [ProjectStatus.NOT_STARTED]: 'Not started',
  [ProjectStatus.SEARCHING]: 'Searching',
  [ProjectStatus.SEARCH_COMPLETE]: 'Search complete',
  [ProjectStatus.STARTED]: 'Started',
  [ProjectStatus.FAILED]: 'Failed',
  [ProjectStatus.COMPLETED]: 'Completed',
  [ProjectStatus.SUMBITTED]: 'Submitted',
}

export enum MappingStatus {
  ORIGINAL_VALUE = 1,
  NO_MAPPABLE_VALUE = 2,
  NO_MAPPER = 3,
  NOT_MAPPED = 4,
  MAPPED = 5,
}
