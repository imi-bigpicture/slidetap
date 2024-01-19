export enum Action {
    NEW = 1,
    VIEW = 2,
    EDIT = 3,
    DELETE = 4,
    RESTORE = 5,
    COPY = 6,
  }

  export const ActionStrings = {
    [Action.NEW]: 'New',
    [Action.VIEW]: 'View',
    [Action.EDIT]: 'Edit',
    [Action.DELETE]: 'Delete',
    [Action.RESTORE]: 'Restore',
    [Action.COPY]: 'Copy',
  }