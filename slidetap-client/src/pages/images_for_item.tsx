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

import { Box } from '@mui/material'
import { ReactElement } from 'react'
import { useParams } from 'react-router-dom'
import ImagesForItem from 'src/components/image/images_for_item_page'

export default function ImagesForItemPage(): ReactElement {
  const { itemUid } = useParams()
  if (itemUid === undefined) {
    throw new Error('Item UID is required to display images for item page')
  }
  return (
    // The view fills what it is given and divides it between the image and the
    // thumbnails, so it has to be given a height: without one the viewer has
    // nothing left after the strip and collapses.
    <Box
      sx={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}
    >
      <ImagesForItem itemUid={itemUid} />
    </Box>
  )
}
