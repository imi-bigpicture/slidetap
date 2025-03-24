import {
  Add,
  Delete,
  Edit,
  FileCopy,
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
}

export default actionsIcons
