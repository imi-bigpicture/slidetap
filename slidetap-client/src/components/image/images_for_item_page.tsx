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
import Grid from '@mui/material/Grid'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { Image } from 'src/models/item'
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
}

export default function ImagesForItem({
  itemUid,
}: ImagesForItemProps): React.ReactElement {
  const rootSchema = useSchemaContext()

  const [selectedImageUid, setSelectedImageUid] = React.useState<string>()
  const [selectedImageSchemaUids, setSelectedImageSchemaUids] = React.useState<
    string[]
  >(Object.keys(rootSchema.images))
  const [selectedGroupBySchemaUid, setSelectedGroupBySchemaUid] = React.useState<
    string | undefined
  >(undefined)
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
    <Grid container spacing={2}>
      <Grid size={12}>
        <Paper elevation={3} sx={{ height: 'calc(100vh - 360px)' }}>
          {selectedImageUid && <OpenSeaDragonViewer imageUid={selectedImageUid} />}
        </Paper>
        <Paper elevation={3} sx={{ p: 1, height: 280 }}>
          {imageGroupsQuery.isLoading || schemaHierarchyQuery.isLoading ? (
            <LinearProgress />
          ) : (
            schemaHierarchyQuery.data && (
              <Box>
                <FormControl sx={{ m: 1, minWidth: 200 }}>
                  <InputLabel id="group-by-schema-label">Group by Schema</InputLabel>
                  <Select
                    labelId="group-by-schema-label"
                    value={selectedGroupBySchemaUid}
                    onChange={(e) => setSelectedGroupBySchemaUid(e.target.value)}
                    label="Group by Schema"
                  >
                    {schemaHierarchyQuery.data.map((schema) => (
                      <MenuItem key={schema.uid} value={schema.uid}>
                        {schema.displayName}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
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
              </Box>
            )
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
              ?.sort((a, b) => a.identifier.localeCompare(b.identifier))
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
                      .sort((a, b) => a.identifier.localeCompare(b.identifier))
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
                                {image.identifier}
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
      </Grid>
    </Grid>
  )
}
