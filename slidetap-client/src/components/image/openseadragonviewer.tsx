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

import { LinearProgress, alpha, useTheme } from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import OpenSeadragon, { DziTileSource } from 'openseadragon'
import React, { useEffect } from 'react'
import type { Theme } from '@mui/material'
import type { Dzi } from 'src/models/dzi'
import imageApi from 'src/services/api/image_api'
import auth from 'src/services/auth'
import { queryKeys } from 'src/services/query_keys'

interface OpenSeaDragonViewerProps {
  imageUid: string
}

function OpenSeaDragonViewer({
  imageUid,
}: OpenSeaDragonViewerProps): React.ReactElement {
  // The element itself rather than an id: two viewers can be on the page at
  // once — an images panel beside an image opened in the detail dock — and a
  // fixed id would have the second one attach to the first one's element.
  const container = React.useRef<HTMLDivElement>(null)
  const theme = useTheme()
  const dziQuery = useQuery({
    queryKey: queryKeys.image.dzi(imageUid),
    queryFn: async () => {
      return await imageApi.getDzi(imageUid)
    },
  })
  useEffect(() => {
    if (dziQuery.data === undefined || container.current === null) {
      return
    }
    const element = container.current
    const viewer = createViewer(dziQuery.data, element, theme)
    // The viewer fits the image to the panel it was built in, and the panel it
    // is built in is rarely the size it ends up: it shares the height with a
    // strip of thumbnails and sits in whatever the window leaves. Fitting again
    // whenever it is resized is what keeps the image in the panel.
    const observer = new ResizeObserver(() => viewer.viewport?.goHome(true))
    observer.observe(element)
    return () => {
      observer.disconnect()
      closeViewer(viewer)
    }
    // Rebuilt on a change of theme: the navigator takes its colours when it is
    // made and does not repaint them.
  }, [dziQuery.data, theme])
  if (dziQuery.data === undefined) {
    return <LinearProgress />
  }
  return (
    <div
      ref={container}
      style={{
        height: '100%',
        width: '100%',
      }}
    />
  )
}
export { OpenSeaDragonViewer }

function createViewer(
  dzi: Dzi,
  element: HTMLElement,
  theme: Theme,
): OpenSeadragon.Viewer {
  const tileSource = new DziTileSource(
    dzi.width,
    dzi.height,
    dzi.tileSize,
    dzi.tileOverlap,
    dzi.url,
    dzi.tileFormat,
    undefined,
    undefined,
    undefined,
  )
  const options = {
    element,
    tileSources: tileSource,
    showZoomControl: false,
    showHomeControl: false,
    showFullPageControl: false,
    zoomPerScroll: 2,
    showNavigator: true,
    // The navigator is black behind the slide otherwise, which reads as bars
    // around a scan that is mostly pale tissue.
    navigatorBackground: theme.palette.background.paper,
    // Enough of an edge to read as a panel once the black is gone: against a
    // pale slide on a pale ground, a divider-coloured border disappears.
    navigatorBorderColor: alpha(theme.palette.text.primary, 0.3),
    navigatorDisplayRegionColor: theme.palette.primary.main,
    ajaxHeaders: auth.getHeaders(),
    loadTilesWithAjax: true,
  }
  return OpenSeadragon(options as OpenSeadragon.Options)
}

function closeViewer(viewer: OpenSeadragon.Viewer): void {
  viewer.close()
  viewer.destroy()
}
