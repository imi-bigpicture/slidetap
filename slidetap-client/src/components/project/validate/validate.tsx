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
  ImageList,
  ImageListItem,
  ImageListItemBar,
  LinearProgress,
} from '@mui/material'
import Container from '@mui/material/Container'
import FormControlLabel from '@mui/material/FormControlLabel'
import FormGroup from '@mui/material/FormGroup'
import FormLabel from '@mui/material/FormLabel'
import Pagination from '@mui/material/Pagination'
import Switch from '@mui/material/Switch'
import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import StepHeader from 'components/step_header'
import type { Image } from 'models/item'
import type { Project } from 'models/project'
import type { Size } from 'models/setting'
import React, { useMemo, useState, type ReactElement } from 'react'
import imageApi from 'services/api/image_api'
import itemApi from 'services/api/item_api'
import Thumbnail from './thumbnail'
import { ValidateImage } from './validate_image'

interface ValidateProps {
  project: Project
}

export default function Validate({ project }: ValidateProps): ReactElement {
  const queryClient = useQueryClient()
  const size: Size = { width: 200, height: 200 }
  const [imageOpen, setImageOpen] = useState(false)
  const [openedImage, setOpenedImage] = useState<Image>()
  const [showIncluded, setShowIncluded] = useState(true)
  const [showExcluded, setShowExcluded] = useState(false)
  const [page, setPage] = useState<number>(1)
  const PER_PAGE = 16
  const PER_ROW = 4
  const imagesWithThumbnailQuery = useQuery({
    queryKey: ['imagesWithThumbnail', project.uid],
    queryFn: async () => {
      return await imageApi.getImagesWithThumbnail(project.uid)
    },
    select: (data: Image[]) => {
      return data.filter((image) => {
        if (showIncluded && image.selected) {
          return true
        }
        if (showExcluded && !image.selected) {
          return true
        }
        return false
      })
    },
    refetchInterval: 10000,
    placeholderData: keepPreviousData,
  })
  const pageCount = useMemo(
    () =>
      imagesWithThumbnailQuery.data !== undefined
        ? Math.ceil(imagesWithThumbnailQuery.data.length / PER_PAGE)
        : 1,
    [imagesWithThumbnailQuery.data],
  )

  function handleOpenImageChange(image: Image): void {
    setOpenedImage(image)
    setImageOpen(true)
  }
  const setIncludeStatus = async ({
    image,
    include,
  }: {
    image: Image
    include: boolean
  }): Promise<Response> => {
    return await itemApi.select(image.uid, include)
  }

  const setIncludeStatusMutation = useMutation({
    mutationFn: setIncludeStatus,
    onSuccess: (data, variables) => {
      queryClient.setQueryData<Image[] | undefined>(
        ['imagesWithThumbnail', project.uid],
        (oldData) =>
          oldData !== undefined
            ? oldData.map((image) => {
                if (image.uid === variables.image.uid) {
                  return { ...image, selected: variables.include }
                }
                return image
              })
            : oldData,
      )
    },
  })
  if (imagesWithThumbnailQuery.data === undefined) {
    return <LinearProgress />
  }

  function handlePageChange(event: React.ChangeEvent<unknown>, page: number): void {
    setPage(page)
  }

  return (
    <Container sx={{ vh: 100 }}>
      <StepHeader title="Validate" description="Validate exported images." />
      <FormGroup>
        <FormLabel>Show</FormLabel>
        <FormGroup row>
          <FormControlLabel
            control={<Switch value={showIncluded} checked={showIncluded} />}
            label="Included"
            onChange={(event, checked) => {
              setShowIncluded(checked)
            }}
          />
          <FormControlLabel
            control={<Switch value={showExcluded} checked={showExcluded} />}
            label="Excluded"
            onChange={(event, checked) => {
              setShowExcluded(checked)
            }}
          />
        </FormGroup>
      </FormGroup>

      <ImageList cols={PER_ROW} rowHeight={size.height}>
        {imagesWithThumbnailQuery.data
          .slice((page - 1) * PER_PAGE, page * PER_PAGE)
          .map((image) => (
            <ImageListItem
              key={image.uid}
              style={{ opacity: !showIncluded || image.selected ? 1 : 0.15 }}
            >
              <Thumbnail
                key={image.uid}
                image={image}
                openImage={handleOpenImageChange}
                size={size}
              />
              <ImageListItemBar title={image.name} />
            </ImageListItem>
          ))}
      </ImageList>
      <Pagination
        count={pageCount}
        size="large"
        page={page}
        variant="outlined"
        shape="rounded"
        onChange={handlePageChange}
        color="primary"
      />
      {openedImage !== undefined && (
        <ValidateImage
          open={imageOpen}
          image={openedImage}
          setOpen={setImageOpen}
          setIncluded={(image: Image, include: boolean) => {
            setIncludeStatusMutation.mutate({ image, include })
          }}
        />
      )}
    </Container>
  )
}
