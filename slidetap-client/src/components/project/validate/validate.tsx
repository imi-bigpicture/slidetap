import { ImageList, ImageListItem, ImageListItemBar } from '@mui/material'
import Container from '@mui/material/Container'
import FormControlLabel from '@mui/material/FormControlLabel'
import FormGroup from '@mui/material/FormGroup'
import FormLabel from '@mui/material/FormLabel'
import Pagination from '@mui/material/Pagination'
import Switch from '@mui/material/Switch'
import StepHeader from 'components/step_header'
import type { ImageDetails } from 'models/item'
import type { Project } from 'models/project'
import type { Size } from 'models/setting'
import React, { useEffect, useState, type ReactElement } from 'react'
import imageApi from 'services/api/image_api'
import itemApi from 'services/api/item_api'
import Thumbnail from './thumbnail'
import { ValidateImage } from './validate_image'

interface ValidateProps {
  project: Project
}

export default function Validate({ project }: ValidateProps): ReactElement {
  const size: Size = { width: 200, height: 200 }
  const [images, setImages] = useState<ImageDetails[]>([])
  const [imageOpen, setImageOpen] = useState(false)
  const [openedImage, setOpenedImage] = useState<ImageDetails>()
  const [showIncluded, setShowIncluded] = useState(true)
  const [showExcluded, setShowExcluded] = useState(false)
  const [page, setPage] = useState<number>(1)
  const [pageCount, setPageCount] = useState<number>(1)
  const PER_PAGE = 16
  const PER_ROW = 4

  useEffect(() => {
    const getImagesWithThumbnail = (): void => {
      imageApi
        .getImagesWithThumbnail(project.uid)
        .then((images) => {
          setImages(images)
          setPageCount(Math.ceil(images.length / PER_PAGE))
        })
        .catch((exception) => {
          console.error('Failed to get image', exception)
        })
    }
    getImagesWithThumbnail()
    const intervalId = setInterval(() => {
      getImagesWithThumbnail()
    }, 10000)
    return () => {
      clearInterval(intervalId)
    }
  }, [project.uid])

  function handleOpenImageChange(image: ImageDetails): void {
    setOpenedImage(image)
    setImageOpen(true)
  }

  function setIncludeStatus(image: ImageDetails, include: boolean): void {
    itemApi.select(image.uid, include).catch((x) => {
      console.error('Failed to select image', x)
    })
    setImages(
      images.map((storedImage) => {
        if (storedImage.uid !== image.uid) {
          return storedImage
        }
        storedImage.selected = !storedImage.selected
        return storedImage
      }),
    )
  }

  function getfilterImages(): ImageDetails[] {
    return images.filter((image) => {
      if (showIncluded && image.selected) {
        return true
      }
      if (showExcluded && !image.selected) {
        return true
      }
      return false
    })
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
        {getfilterImages()
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
          setIncluded={setIncludeStatus}
        />
      )}
    </Container>
  )
}
