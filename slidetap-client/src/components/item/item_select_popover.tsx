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

import { Cancel, Delete, RestoreFromTrash } from '@mui/icons-material'
import {
  Button,
  FormControl,
  Paper,
  Popover,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useState, type ReactElement } from 'react'
import type { ItemSelect } from 'src/models/item_select'
import DisplayItemTags from './display_item_tags'

interface ItemSelectPopoverProps {
  /** Anchor to open against. The popover is open while this is set. */
  anchorEl: HTMLElement | null
  /** What confirming does: restore the items to the project, or remove them. */
  select: boolean
  comment: string | null
  tags: string[] | null
  /** Add the tags to whatever the items already carry, rather than replacing. */
  additiveTags: boolean
  /** What is being removed or restored, as it is to be read: one item's
   * identifier, or how many of what. The popover is opened from a bin icon
   * that has no room to say, so it says it here. */
  subject?: string
  onConfirm: (value: ItemSelect) => void
  onClose: () => void
}

/**
 * Confirms deleting items from the project or restoring them, and collects the
 * comment and tags to record with it. Shared by the item tables and the item
 * detail view so both ask the same question in the same way.
 *
 * Mount it only while open: the comment and tags start from the props.
 */
export default function ItemSelectPopover({
  anchorEl,
  select,
  comment: initialComment,
  tags: initialTags,
  additiveTags,
  subject,
  onConfirm,
  onClose,
}: ItemSelectPopoverProps): ReactElement {
  const [comment, setComment] = useState(initialComment)
  const [tags, setTags] = useState<string[]>(initialTags ?? [])
  const [newTagNames, setNewTagNames] = useState<string[]>([])

  return (
    <Popover
      open={anchorEl !== null}
      anchorEl={anchorEl}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      transformOrigin={{ vertical: -10, horizontal: 'center' }}
    >
      <Paper sx={{ p: 2, borderRadius: 2, maxWidth: 300 }}>
        {subject !== undefined && (
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {select
              ? `Restore ${subject} to the project?`
              : `Remove ${subject} from the project?`}
          </Typography>
        )}
        <FormControl component="fieldset" variant="standard">
          <Stack spacing={1} direction="column">
            <TextField
              label="Comment"
              size="small"
              value={comment ?? ''}
              onChange={(event) => setComment(event.target.value)}
              fullWidth
            />
            <DisplayItemTags
              tagUids={tags}
              newTagNames={newTagNames}
              editable={true}
              handleTagsUpdate={setTags}
              setNewTags={setNewTagNames}
            />
          </Stack>
        </FormControl>
        <Stack direction="row" spacing={1} sx={{ mt: 2, justifyContent: 'center' }}>
          <Tooltip title={select ? 'Restore' : 'Remove'}>
            <Button onClick={() => onConfirm({ select, comment, tags, additiveTags })}>
              {select ? <RestoreFromTrash /> : <Delete />}
            </Button>
          </Tooltip>
          <Tooltip title="Cancel">
            <Button onClick={onClose}>
              <Cancel />
            </Button>
          </Tooltip>
        </Stack>
      </Paper>
    </Popover>
  )
}
