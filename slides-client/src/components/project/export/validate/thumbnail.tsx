import React, { useEffect, type ReactElement } from 'react'
import { ImageListItem, ImageListItemBar } from '@mui/material'
import type { Image } from 'models/items'
import type { Project } from 'models/project'
import imageApi from 'services/api/image_api'
import Spinner from 'components/spinner'
import type { Size } from 'models/setting'

interface ThumbnailProps {
  project: Project
  image: Image
  openImage: (image: Image) => void
  size: Size
  dimExcluded: boolean
}

export default function Thumbnail({
  project,
  image,
  openImage,
  size,
  dimExcluded,
}: ThumbnailProps): ReactElement {
  const [thumbnail, setThumbnail] = React.useState<string>()
  const [loading, setLoading] = React.useState<boolean>(true)
  useEffect(() => {
    const getThumbnail = (): void => {
      imageApi
        .getThumbnail(image.uid, [200, 200])
        .then((thumbnail) => {
          setThumbnail(URL.createObjectURL(thumbnail))
          setLoading(false)
        })
        .catch((x) => {console.error('Failed to get thumbnail', x)})
    }
    getThumbnail()
  }, [image.uid])

  function handleOnClick(event: React.MouseEvent<HTMLImageElement>): void {
    openImage(image)
  }

  const style = { opacity: !dimExcluded || image.selected ? 1 : 0.15 }

  return (
    <Spinner loading={loading} minHeight={size.height.toString() + 'px'}>
      <ImageListItem style={style}>
        <img src={thumbnail} loading="lazy" alt={image.name} onClick={handleOnClick} />
        <ImageListItemBar title={image.name} />
      </ImageListItem>
    </Spinner>
  )
}
