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

import {
  Add,
  Delete,
  Edit,
  FileCopy,
  OpenInNew,
  PhotoLibrary,
  Replay,
  RestoreFromTrash,
  Visibility,
} from '@mui/icons-material'
import { Select } from '@mui/material'
import { Action } from 'src/models/action'

const actionsIcons = {
  [Action.NEW]: <Add />,
  [Action.VIEW]: <Visibility />,
  [Action.EDIT]: <Edit />,
  [Action.RESTORE]: <RestoreFromTrash />,
  [Action.DELETE]: <Delete />,
  [Action.COPY]: <FileCopy />,
  [Action.SELECT]: <Select />,
  [Action.RETRY]: <Replay />,
  [Action.IMAGES]: <PhotoLibrary />,
  [Action.WINDOW]: <OpenInNew />,
}

export default actionsIcons
