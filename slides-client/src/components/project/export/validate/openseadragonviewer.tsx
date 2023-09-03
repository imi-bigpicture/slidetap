import { Dzi } from 'models/dzi'
import OpenSeadragon, { DziTileSource } from 'openseadragon'
import React, { ReactElement, useEffect, useState } from 'react'
import imageApi from 'services/api/image_api'

interface OpenSeaDragonViewerProps {
  imageUid: string
}

function OpenSeaDragonViewer({ imageUid }: OpenSeaDragonViewerProps): ReactElement {
  const [dzi, setDzi] = useState<Dzi | null>(null)
  useEffect(() => {
    const getDzi = (): void => {
      imageApi
        .getDzi(imageUid)
        .then((dzi) => setDzi(dzi))
        .catch((x) => console.error('Failed to get dzi', x))
    }
    getDzi()
  }, [imageUid])
  useEffect(() => {
    if (dzi === null) {
      return
    }
    const viewer = createViewer(dzi)
    return () => {
      closeViewer(viewer)
    }
  }, [dzi])
  return (
    <div
      id="viewer"
      style={{
        height: '90%',
        width: '100%',
      }}
    />
  )
}
export { OpenSeaDragonViewer }

function createViewer(dzi: Dzi): OpenSeadragon.Viewer {
  const tileSource = new DziTileSource(
    dzi.width,
    dzi.height,
    dzi.tileSize,
    dzi.tileOverlap,
    // @ts-expect-error
    dzi.url,
    dzi.tileFormat,
    undefined,
    undefined,
    undefined,
  )
  const options = {
    id: 'viewer',
    tileSources: tileSource,
    showZoomControl: false,
    showHomeControl: false,
    showFullPageControl: false,
    zoomPerScroll: 2,
    showNavigator: true,
  }
  return OpenSeadragon(options)
}

function closeViewer(viewer: OpenSeadragon.Viewer): void {
  viewer.close()
  viewer.destroy()
}
