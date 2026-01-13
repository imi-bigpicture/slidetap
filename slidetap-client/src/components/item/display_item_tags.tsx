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

import { Cancel, Save } from '@mui/icons-material'
import {
  Autocomplete,
  Button,
  Chip,
  FormControl,
  LinearProgress,
  Paper,
  Popover,
  Stack,
  TextField,
  Tooltip,
} from '@mui/material'
import { ArrowDropDownIcon } from '@mui/x-date-pickers'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { MuiColorInput } from 'mui-color-input'
import React, { useState } from 'react'
import { Tag } from 'src/models/tag'
import tagApi from 'src/services/api/tag_api'

interface DisplayItemTagsProps {
  tagUids: string[]
  newTagNames: string[]
  editable: boolean
  handleTagsUpdate: (tags: string[]) => void
  setNewTags: (names: string[]) => void
}

export default function DisplayItemTags({
  tagUids,
  newTagNames,
  editable,
  handleTagsUpdate,
  setNewTags,
}: DisplayItemTagsProps): React.JSX.Element {
  const queryClient = useQueryClient()
  const [tagEditAnchorEl, setTageEditAnchorEl] = useState<HTMLDivElement | null>(null)
  const [openedEditTag, setOpenedEditTag] = useState<Tag | null>(null)
  const tagEditOpen = Boolean(tagEditAnchorEl)

  const handleTagEditClick = (
    event: React.MouseEvent<HTMLDivElement, MouseEvent>,
    tag: Tag,
  ) => {
    setTageEditAnchorEl(event.currentTarget)
    setOpenedEditTag(tag)
  }

  const handleTagEditClose = () => {
    setOpenedEditTag(null)
    setTageEditAnchorEl(null)
  }

  const tagsQuery = useQuery({
    queryKey: ['tags'],
    queryFn: async () => {
      return await tagApi.getTags()
    },
  })

  const saveMutation = useMutation({
    mutationFn: async (tag: Tag) => {
      return await tagApi.save(tag)
    },
    onSuccess: (data) => {
      queryClient.setQueryData(['tags'], (old: Tag[] | undefined) => {
        if (!old) return [data]
        return old.map((tag) => (tag.uid === data.uid ? data : tag))
      })
      setOpenedEditTag(null)
      setTageEditAnchorEl(null)
    },
  })
  if (tagsQuery.data === undefined) {
    if (tagsQuery.isLoading) {
      return <LinearProgress />
    } else {
      return <></>
    }
  }
  const tags = tagUids
    .map((uid) => tagsQuery.data.find((tag) => tag.uid === uid))
    .filter((tag): tag is Tag => tag !== undefined)
    .concat(
      newTagNames.map((name) => ({
        uid: '00000000-0000-0000-0000-000000000000',
        name: name,
        description: '',
        color: '',
      })),
    )
  return (
    <React.Fragment>
      <Autocomplete
        multiple
        options={tagsQuery.data}
        getOptionLabel={(option) => (typeof option === 'string' ? option : option.name)}
        // value={tags.map((tag) => {
        //   const foundTag = tagsQuery.data.find((t) => t.uid === tag)
        //   return foundTag
        //     ? foundTag
        //     : { uid: '00000000-0000-0000-0000-000000000000', name: tag }
        // })}
        value={tags}
        freeSolo
        onChange={async (_, newValue) => {
          const newTags = newValue.filter((tag) => typeof tag === 'string')
          setNewTags(newTags)
          const updatedTags = newValue
            .filter((tag) => typeof tag !== 'string')
            .map((tag) => tag.uid)
          handleTagsUpdate(updatedTags)
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Tags"
            size="small"
            placeholder={editable ? 'Add tag' : undefined}
          />
        )}
        size="small"
        readOnly={!editable}
        autoComplete={true}
        autoHighlight={true}
        fullWidth={true}
        selectOnFocus
        clearOnBlur
        handleHomeEndKeys
        popupIcon={editable ? <ArrowDropDownIcon /> : null}
        renderTags={(value, getTagProps) => (
          <React.Fragment>
            {value.map((tag, index) => {
              const { key, ...other } = getTagProps({ index })
              return (
                <Tooltip title={tag.description ?? undefined} key={key}>
                  <Chip
                    {...other}
                    label={tag.name}
                    style={tag.color ? { backgroundColor: tag.color } : undefined}
                    onClick={(event) => handleTagEditClick(event, tag)}
                  />
                </Tooltip>
              )
            })}
          </React.Fragment>
        )}
      />

      <Popover
        open={tagEditOpen}
        anchorEl={tagEditAnchorEl}
        onClose={handleTagEditClose}
        anchorOrigin={{
          vertical: 'bottom',
          horizontal: 'center',
        }}
        transformOrigin={{
          vertical: -10,
          horizontal: 'center',
        }}
      >
        <Paper sx={{ p: 2 }} style={{ maxWidth: '300px' }} square={false}>
          <FormControl component="fieldset" variant="standard">
            <Stack spacing={1} direction="column">
              <Stack direction="row" spacing={1}>
                <TextField
                  label="Name"
                  size="small"
                  value={openedEditTag?.name ?? ''}
                  onChange={(event) => {
                    setOpenedEditTag(
                      openedEditTag
                        ? { ...openedEditTag, name: event.target.value }
                        : null,
                    )
                  }}
                  fullWidth
                />
                <MuiColorInput
                  label="Color"
                  value={openedEditTag?.color ?? ''}
                  onChange={(color) => {
                    setOpenedEditTag(
                      openedEditTag
                        ? {
                            ...openedEditTag,
                            color: color,
                          }
                        : null,
                    )
                  }}
                  size="small"
                  format={'hex'}
                  isAlphaHidden={true}
                />
              </Stack>
              <TextField
                label="Description"
                size="small"
                value={openedEditTag?.description ?? undefined}
                onChange={(event) => {
                  setOpenedEditTag(
                    openedEditTag
                      ? { ...openedEditTag, description: event.target.value }
                      : null,
                  )
                }}
              />
            </Stack>
          </FormControl>
          <Stack direction="row" spacing={1} sx={{ mt: 2, justifyContent: 'center' }}>
            <Button
              onClick={() => {
                if (openedEditTag) {
                  saveMutation.mutate(openedEditTag)
                }
              }}
            >
              <Save />
            </Button>
            <Button onClick={handleTagEditClose}>
              <Cancel />
            </Button>
          </Stack>
        </Paper>
      </Popover>
    </React.Fragment>
  )
}
