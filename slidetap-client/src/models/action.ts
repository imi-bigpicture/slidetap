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

export enum Action {
  NEW = 1,
  VIEW = 2,
  EDIT = 3,
  DELETE = 4,
  RESTORE = 5,
  COPY = 6,
  SELECT = 7,
  RETRY = 8,
  IMAGES = 9,
  WINDOW = 10,
}

export const ActionStrings = {
  [Action.NEW]: 'New',
  [Action.VIEW]: 'View',
  [Action.EDIT]: 'Edit',
  [Action.DELETE]: 'Delete',
  [Action.RESTORE]: 'Restore',
  [Action.COPY]: 'Copy',
  [Action.SELECT]: 'Select',
  [Action.RETRY]: 'Retry',
  [Action.IMAGES]: 'Images',
  [Action.WINDOW]: 'Open in new window',
}

export enum ItemDetailAction {
  VIEW = Action.VIEW,
  EDIT = Action.EDIT,
}