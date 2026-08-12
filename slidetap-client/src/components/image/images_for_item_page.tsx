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
  Box,
  Card,
  CardActionArea,
  CardContent,
  CardMedia,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Paper,
  Select,
  Typography,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { Image } from 'src/models/item'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import { Size } from 'src/models/setting'
import imageApi from 'src/services/api/image_api'
import itemApi from 'src/services/api/item_api'
import schemaApi from 'src/services/api/schema_api'
import { queryKeys } from 'src/services/query_keys'
import { OpenSeaDragonViewer } from './openseadragonviewer'

interface ThumbnailProps {
  image: Image
  size: Size
}

function ThumbnailCardMedia({ image, size }: ThumbnailProps): React.ReactElement {
  const thumbnailQuery = useQuery({
    queryKey: queryKeys.image.thumbnail(image.uid, size),
    queryFn: async () => {
      return await imageApi.getThumbnail(image.uid, size)
    },
  })

  if (thumbnailQuery.data === undefined) {
    return <LinearProgress />
  }

  return (
    <CardMedia
      component="img"
      height="100"
      src={URL.createObjectURL(thumbnailQuery.data)}
      alt={image.name ?? image.identifier}
    />
  )
}

interface ImagesForItemProps {
  itemUid: string
  /** What to group by. The item's own schema when not given, and a control to
   * choose with — a caller that says which one has already chosen. */
  groupBySchemaUid?: string
  /** Which images to show, on the same terms: all of them and a control to
   * pick from when not given. */
  imageSchemaUids?: string[]
}

export default function ImagesForItem({
  itemUid,
  groupBySchemaUid,
  imageSchemaUids,
}: ImagesForItemProps): React.ReactElement {
  const { pseudonymMode } = usePseudonym()
  const rootSchema = useSchemaContext()

  const [selectedImageUid, setSelectedImageUid] = React.useState<string>()
  const [selectedImageSchemaUids, setSelectedImageSchemaUids] = React.useState<
    string[]
  >(imageSchemaUids ?? Object.keys(rootSchema.images))
  const showControls = groupBySchemaUid === undefined || imageSchemaUids === undefined
  const [selectedGroupBySchemaUid, setSelectedGroupBySchemaUid] = React.useState<
    string | undefined
  >(groupBySchemaUid)
  const itemQuery = useQuery({
    queryKey: queryKeys.item.detail(itemUid),
    queryFn: async () => {
      const item = await itemApi.get(itemUid)
      if (selectedGroupBySchemaUid === undefined) {
        setSelectedGroupBySchemaUid(item.schemaUid)
      }
      return item
    },
  })
  const imageGroupsQuery = useQuery({
    queryKey: queryKeys.image.forItem(itemUid, selectedGroupBySchemaUid ?? ''),
    queryFn: async () => {
      if (selectedGroupBySchemaUid === undefined) {
        return undefined
      }
      const groups = await itemApi.getImagesForitem(itemUid, selectedGroupBySchemaUid)
      if (selectedImageUid === undefined) {
        setSelectedImageUid(groups[0]?.images[0]?.uid)
      }
      return await groups
    },
    enabled: itemQuery.data !== undefined && selectedGroupBySchemaUid !== undefined,
  })
  const schemaHierarchyQuery = useQuery({
    queryKey: queryKeys.schema.hierarchy(itemQuery.data?.schemaUid ?? ''),
    queryFn: async () => {
      if (itemQuery.data === undefined) {
        return undefined
      }
      return await schemaApi.getSchemaHierarchy(itemQuery.data.schemaUid)
    },
    enabled: itemQuery.data !== undefined,
  })

  return (
    // Fills what it is given rather than measuring itself against the window:
    // the same view is a page of its own and one panel of a tab, and only the
    // container knows which.
    <Box
      sx={{
        height: '100%',
        minHeight: 0,
        // Bounded sideways as well: the strip of thumbnails is as wide as the
        // case has images, and without this it is the strip that decides how
        // wide the viewer is.
        width: '100%',
        minWidth: 0,
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Paper elevation={3} sx={{ flex: 1, minHeight: 0 }}>
        {selectedImageUid && <OpenSeaDragonViewer imageUid={selectedImageUid} />}
      </Paper>
      <Paper
        elevation={3}
        sx={{
          p: 1,
          height: showControls ? 280 : 220,
          flexShrink: 0,
          minWidth: 0,
          overflow: 'auto',
        }}
      >
        {/* Outside the controls: the thumbnails take a moment to arrive
            whether or not there is anything to choose. */}
        {(imageGroupsQuery.isLoading || schemaHierarchyQuery.isLoading) && (
          <LinearProgress />
        )}
        {showControls && schemaHierarchyQuery.data !== undefined && (
          <Box>
            {groupBySchemaUid === undefined && (
              <FormControl sx={{ m: 1, minWidth: 200 }}>
                <InputLabel id="group-by-schema-label">Group by Schema</InputLabel>
                <Select
                  labelId="group-by-schema-label"
                  value={selectedGroupBySchemaUid}
                  onChange={(e) => setSelectedGroupBySchemaUid(e.target.value)}
                  label="Group by Schema"
                >
                  {/* In the order the hierarchy gives them, which is what
                          the list is: the item, then what hangs under it. */}
                  {schemaHierarchyQuery.data.map((schema) => (
                    <MenuItem key={schema.uid} value={schema.uid}>
                      {schema.displayName}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
            {imageSchemaUids === undefined && (
              <FormControl sx={{ m: 1, minWidth: 200 }}>
                <InputLabel id="image-schema-label">Show image schemas</InputLabel>
                <Select
                  labelId="image-schema-label"
                  value={selectedImageSchemaUids}
                  onChange={(e) => {
                    if (Array.isArray(e.target.value)) {
                      setSelectedImageSchemaUids(e.target.value)
                    } else {
                      setSelectedImageSchemaUids([e.target.value])
                    }
                  }}
                  label="Image schema"
                  multiple={true}
                >
                  {Object.values(rootSchema.images).map((schema) => (
                    <MenuItem key={schema.uid} value={schema.uid}>
                      {schema.displayName}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            )}
          </Box>
        )}
        <Box
          sx={{
            height: '200',
            width: '100%',
            overflowX: 'auto',
            overflowY: 'hidden',
            display: 'flex',
            flexDirection: 'row',
            gap: 1.5,
            alignItems: 'flex-start',
          }}
        >
          {imageGroupsQuery.data
            ?.map((group) => ({
              ...group,
              images: group.images.filter((image) =>
                selectedImageSchemaUids.includes(image.schemaUid),
              ),
            }))
            .filter((group) => group.images.length > 0)
            .sort((a, b) => a.identifier.localeCompare(b.identifier))
            .map((group) => (
              <Paper
                key={group.identifier}
                sx={{
                  p: 0.5,
                  display: 'inline-block',
                }}
                elevation={1}
                square={false}
              >
                <Typography variant="h6">{group.identifier}</Typography>
                <Box sx={{ display: 'flex', flexWrap: 'nowrap', gap: 0.5 }}>
                  {group.images
                    .sort((a, b) =>
                      getDisplayIdentifier(a, pseudonymMode).localeCompare(
                        getDisplayIdentifier(b, pseudonymMode),
                      ),
                    )
                    .map((image) => (
                      <Card key={image.uid}>
                        <CardActionArea
                          sx={{
                            width: 150,
                            cursor: 'pointer',
                            boxShadow:
                              selectedImageUid === image.uid
                                ? '0px 0px 0px 2px #1976d2 inset'
                                : 'none',
                            p: 0.5,
                          }}
                          onClick={() => setSelectedImageUid(image.uid)}
                        >
                          <ThumbnailCardMedia
                            image={image}
                            size={{ width: 200, height: 200 }}
                          />
                          <CardContent sx={{ p: 0.5 }}>
                            <Typography variant="body2" noWrap>
                              {getDisplayIdentifier(image, pseudonymMode)}
                            </Typography>
                          </CardContent>
                        </CardActionArea>
                      </Card>
                    ))}
                </Box>
              </Paper>
            ))}
        </Box>
      </Paper>
    </Box>
  )
}
