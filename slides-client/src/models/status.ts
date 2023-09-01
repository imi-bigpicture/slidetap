export enum ImageStatus {
    NOT_STARTED = 1,
    DOWNLOADING = 2,
    PROCESSING = 3,
    FAILED = 4,
    COMPLETED = 5
}

export const ImageStatusStrings: { [index: number]: string } = {
    [ImageStatus.NOT_STARTED]: 'Not started',
    [ImageStatus.DOWNLOADING]: 'Downloading',
    [ImageStatus.PROCESSING]: 'Processing',
    [ImageStatus.FAILED]: 'Failed',
    [ImageStatus.COMPLETED]: 'Completed'
}

export enum ProjectStatus {
    NOT_STARTED = 1,
    SEARCHING = 2,
    SEARCH_COMPLETE = 3,
    STARTED = 4,
    FAILED = 5,
    COMPLETED = 6,
    SUMBITTED = 7
}

export const ProjectStatusStrings: { [index: number]: string } = {
    [ProjectStatus.NOT_STARTED]: 'Not started',
    [ProjectStatus.SEARCHING]: 'Searching',
    [ProjectStatus.SEARCH_COMPLETE]: 'Search complete',
    [ProjectStatus.STARTED]: 'Started',
    [ProjectStatus.FAILED]: 'Failed',
    [ProjectStatus.COMPLETED]: 'Completed',
    [ProjectStatus.SUMBITTED]: 'Submitted'
}

export enum MappingStatus {
    NOT_MAPPABLE = 1,
    NO_MAPPER = 2,
    NOT_MAPPED = 3,
    MAPPED = 4
}
