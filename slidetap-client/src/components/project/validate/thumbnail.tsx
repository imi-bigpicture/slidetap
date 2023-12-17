import React, { useEffect, type ReactElement } from 'react'
import type { Image } from 'models/items'
import imageApi from 'services/api/image_api'
import Spinner from 'components/spinner'
import type { Size } from 'models/setting'

interface ThumbnailProps {
  image: Image
  openImage: (image: Image) => void
  size: Size
}

export default function Thumbnail({
  image,
  openImage,
  size,
}: ThumbnailProps): ReactElement {
  const [thumbnail, setThumbnail] = React.useState<string>()
  const [loading, setLoading] = React.useState<boolean>(true)
  useEffect(() => {
    const getThumbnail = (): void => {
      imageApi
        .getThumbnail(image.uid, size)
        .then((thumbnail) => {
          setThumbnail(URL.createObjectURL(thumbnail))
          setLoading(false)
        })
        .catch((x) => {
          console.error('Failed to get thumbnail', x)
        })
    }
    getThumbnail()
  }, [image.uid, size])

  function handleOnClick(event: React.MouseEvent<HTMLImageElement>): void {
    openImage(image)
  }

  return (
    <Spinner loading={loading} minHeight={size.height.toString() + 'px'}>
      <img src={thumbnail} loading="lazy" alt={image.name} onClick={handleOnClick} />
    </Spinner>
  )
}
