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

import { LinearProgress } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import OpenSeadragon, { DziTileSource } from 'openseadragon'
import React, { useEffect } from 'react'
import type { Dzi } from 'src/models/dzi'
import imageApi from 'src/services/api/image_api'
import auth from 'src/services/auth'

interface OpenSeaDragonViewerProps {
  imageUid: string
}

function OpenSeaDragonViewer({
  imageUid,
}: OpenSeaDragonViewerProps): React.ReactElement {
  const dziQuery = useQuery({
    queryKey: ['dzi', imageUid],
    queryFn: async () => {
      return await imageApi.getDzi(imageUid)
    },
  })
  useEffect(() => {
    if (dziQuery.data === undefined) {
      return
    }
    const viewer = createViewer(dziQuery.data)
    return () => {
      closeViewer(viewer)
    }
  }, [dziQuery.data])
  if (dziQuery.data === undefined) {
    return <LinearProgress />
  }
  return (
    <div
      id="viewer"
      style={{
        height: '100%',
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
    ajaxHeaders: auth.getHeaders(),
    loadTilesWithAjax: true,
  }
  return OpenSeadragon(options)
}

function closeViewer(viewer: OpenSeadragon.Viewer): void {
  viewer.close()
  viewer.destroy()
}
