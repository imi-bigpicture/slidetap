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
  AccountTree,
  Add,
  Delete,
  Edit,
  FileCopy,
  OpenInNew,
  Flag,
  LockOpen,
  PhotoLibrary,
  RateReview,
  Replay,
  RestoreFromTrash,
  TableChart,
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
  [Action.OVERVIEW]: <TableChart />,
  [Action.REVIEW]: <Flag sx={{ color: 'error.main', opacity: 0.7 }} />,
  [Action.MARK_REVIEWED]: <Flag sx={{ color: 'success.main', opacity: 0.7 }} />,
  [Action.OPEN_REVIEW]: <RateReview />,
  [Action.HIERARCHY]: <AccountTree />,
  [Action.REOPEN]: <LockOpen />,
}

export default actionsIcons
