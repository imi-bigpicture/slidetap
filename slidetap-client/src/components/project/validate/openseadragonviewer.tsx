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

import type { Dzi } from 'models/dzi'
import OpenSeadragon, { DziTileSource } from 'openseadragon'
import React, { type ReactElement, useEffect, useState } from 'react'
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
        .then((dzi) => {setDzi(dzi)})
        .catch((x) => {console.error('Failed to get dzi', x)})
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
    // @ts-expect-error TODO
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
