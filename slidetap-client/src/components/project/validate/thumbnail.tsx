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

import { FormControl, FormLabel, LinearProgress, Stack } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import Spinner from 'components/spinner'
import type { ImageDetails } from 'models/item'
import type { Size } from 'models/setting'
import React, { type ReactElement } from 'react'
import imageApi from 'services/api/image_api'

interface ThumbnailProps {
  image: ImageDetails
  openImage: (image: ImageDetails) => void
  size: Size
}

export default function Thumbnail({
  image,
  openImage,
  size,
}: ThumbnailProps): ReactElement {
  const thumbnailQuery = useQuery({
    queryKey: ['thumbnail', image.uid, size],
    queryFn: async () => {
      return await imageApi.getThumbnail(image.uid, size)
    },
  })

  if (thumbnailQuery.data === undefined) {
    return <LinearProgress />
  }

  function handleOnClick(event: React.MouseEvent<HTMLImageElement>): void {
    openImage(image)
  }

  return (
    <FormControl component="fieldset" variant="standard">
      <Stack direction="column" spacing={1}>
        <FormLabel>Image</FormLabel>
        <Spinner
          loading={thumbnailQuery.isLoading}
          minHeight={size.height.toString() + 'px'}
        >
          <img
            src={URL.createObjectURL(thumbnailQuery.data)}
            loading="lazy"
            alt={image.name}
            onClick={handleOnClick}
          />
        </Spinner>
      </Stack>
    </FormControl>
  )
}
