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
  LinearProgress,
  Paper,
  Typography,
  alpha,
} from '@mui/material'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import { Image } from 'src/models/item'
import type { AttributeValueLayout } from 'src/models/schema/attribute_value_layout'
import { ImageOrder, type ImagesLayout } from 'src/models/schema/images_layout'
import { AttributeValueField } from 'src/models/table_item'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import { Size } from 'src/models/setting'
import imageApi from 'src/services/api/image_api'
import itemApi from 'src/services/api/item_api'
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

/** The values a layout asked for, in the order it asked for them. */
function shownValues(
  attributes: Record<string, Attribute<AttributeValueTypes>>,
  wanted: AttributeValueLayout[],
): string[] {
  return wanted
    .map(({ tag, field }) => {
      const attribute = attributes[tag]
      // The mapped value says what the item means, the mappable one what it
      // arrived as — which is what the systems it came from show.
      return field === AttributeValueField.MAPPABLE
        ? (attribute?.mappableValue ?? '')
        : (attribute?.displayValue ?? '')
    })
    .filter((value) => value !== '')
}

/** What is said beside an identifier: nothing, or the values in brackets. */
function beside(values: string[]): string {
  return values.length === 0 ? '' : ` (${values.join(', ')})`
}

interface ImagesForItemProps {
  itemUid: string
  /** What to show and how to gather it. The item's own kind is grouped by when
   * there is no layout for it, with controls to choose otherwise. */
  layout?: ImagesLayout
}

export default function ImagesForItem({
  itemUid,
  layout: given,
}: ImagesForItemProps): React.ReactElement {
  const { pseudonymMode } = usePseudonym()
  const rootSchema = useSchemaContext()

  const [chosenImageUid, setChosenImageUid] = React.useState<string>()
  const itemQuery = useQuery({
    queryKey: queryKeys.item.detail(itemUid),
    queryFn: async () => await itemApi.get(itemUid),
  })
  // The layout the caller named, or the one the schema defines for this kind of
  // item. Worked out from the item rather than set when it arrives: the item
  // may already be in hand, and then nothing arrives to set it.
  const layout =
    given ??
    rootSchema.imagesLayouts.find(
      (candidate) => candidate.schemaUid === itemQuery.data?.schemaUid,
    )
  // As the layout says, or by the item's own kind where nothing is laid out
  // for it, which puts everything under it in one group.
  const groupBySchemaUid = layout?.groupBySchemaUid ?? itemQuery.data?.schemaUid
  const imageGroupsQuery = useQuery({
    queryKey: queryKeys.image.forItem(itemUid, groupBySchemaUid ?? '', layout?.uid),
    queryFn: async () => {
      if (groupBySchemaUid === undefined) {
        return undefined
      }
      return await itemApi.getImagesForitem(itemUid, groupBySchemaUid, layout?.uid)
    },
    enabled: groupBySchemaUid !== undefined,
  })

  const groups = (imageGroupsQuery.data ?? [])
    .slice()
    .sort((a, b) => a.identifier.localeCompare(b.identifier))
  /** What an image is put in order by: what it is called, or what it is named
   * where the layout asks for that and there is a name to use. Never in
   * pseudonym mode, where only the pseudonym is to be shown. */
  const order = (image: Image): string =>
    layout?.imageOrder === ImageOrder.Name && !pseudonymMode
      ? (image.name ?? image.identifier)
      : getDisplayIdentifier(image, pseudonymMode)

  // What is in the viewer: what was clicked, or the first thumbnail until
  // something is.
  const selectedImageUid = chosenImageUid ?? groups[0]?.images[0]?.image.uid

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
        // The gallery lies over the image rather than beside it, so the strip
        // is placed against this.
        position: 'relative',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <Paper elevation={3} sx={{ flex: 1, minHeight: 0 }}>
        {selectedImageUid && <OpenSeaDragonViewer imageUid={selectedImageUid} />}
      </Paper>
      <Paper
        elevation={3}
        sx={(theme) => ({
          // Over the foot of the image and let through: the slide is what the
          // panel is for, and the thumbnails take a strip of it whether they
          // are opaque or not. Blurred behind, so tissue under the labels does
          // not make them hard to read.
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: alpha(theme.palette.background.paper, 0.75),
          backdropFilter: 'blur(6px)',
          px: 1,
          pt: 1,
          // Little room under the bar: it belongs to the strip it scrolls, and
          // padding below it reads as a gap between the two.
          pb: 0.25,
          // As tall as the thumbnails, so the scrollbar sits under the group
          // it scrolls rather than at the foot of a band of empty panel. The
          // minimum is what one row of them comes to, so the strip does not
          // grow into place as they arrive and shift the image above it.
          minHeight: 190,
          flexShrink: 0,
          minWidth: 0,
          display: 'flex',
          alignItems: 'flex-start',
          gap: 1,
        })}
      >
        <Box
          sx={(theme) => ({
            flex: 1,
            minWidth: 0,
            overflowX: 'auto',
            // Room between the thumbnails and the bar under them: the bar sits
            // on the edge of this box, and against the pictures it reads as
            // part of them.
            pb: 1,
            overflowY: 'hidden',
            display: 'flex',
            flexDirection: 'row',
            gap: 1.5,
            alignItems: 'flex-start',
            // A slim bar rather than the platform's: it runs the width of the
            // gallery under the thumbnails, where a full-height one is a bar of
            // furniture across the view. Kept rather than hidden — sideways is
            // not where a scroll is looked for, so something has to say the
            // strip goes on.
            scrollbarWidth: 'thin',
            scrollbarColor: `${alpha(theme.palette.text.primary, 0.25)} transparent`,
            '&::-webkit-scrollbar': { height: 6 },
            '&::-webkit-scrollbar-track': { backgroundColor: 'transparent' },
            '&::-webkit-scrollbar-thumb': {
              backgroundColor: alpha(theme.palette.text.primary, 0.25),
              borderRadius: 3,
            },
            '&::-webkit-scrollbar-thumb:hover': {
              backgroundColor: alpha(theme.palette.text.primary, 0.4),
            },
          })}
        >
          {/* The thumbnails take a moment to arrive, and the strip is where
              that is waited for. */}
          {imageGroupsQuery.isLoading && <LinearProgress sx={{ width: '100%' }} />}
          {/* No box around a group: the thumbnails inside are boxed already,
              and one outline within another is a border either way. What marks
              a group is its name over its own thumbnails, and a rule between
              it and the next. */}
          {groups.map((group, index) => (
            <Box
              key={group.identifier}
              sx={{
                display: 'inline-block',
                pl: index === 0 ? 0 : 1.5,
                borderLeft: index === 0 ? 0 : 1,
                borderColor: 'divider',
              }}
            >
              <Typography
                variant="subtitle2"
                color="text.secondary"
                noWrap
                sx={{ px: 0.5, pb: 0.5 }}
              >
                {group.label}
                {beside(shownValues(group.attributes, layout?.groupAttributes ?? []))}
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'nowrap', gap: 0.5 }}>
                {group.images
                  .slice()
                  .sort((a, b) =>
                    order(a.image).localeCompare(order(b.image), undefined, {
                      numeric: true,
                    }),
                  )
                  .map(({ image, attributes }) => {
                    const values = shownValues(
                      attributes,
                      layout?.imageAttributes ?? [],
                    )
                    return (
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
                          onClick={() => setChosenImageUid(image.uid)}
                        >
                          <ThumbnailCardMedia
                            image={image}
                            size={{ width: 200, height: 200 }}
                          />
                          {/* Two lines rather than one: an identifier and a
                            stain code do not fit across a thumbnail, and
                            neither is worth cutting off. */}
                          <CardContent sx={{ p: 0.5 }}>
                            <Typography variant="body2" noWrap>
                              {getDisplayIdentifier(image, pseudonymMode)}
                            </Typography>
                            {values.length > 0 && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                noWrap
                              >
                                {values.join(' · ')}
                              </Typography>
                            )}
                          </CardContent>
                        </CardActionArea>
                      </Card>
                    )
                  })}
              </Box>
            </Box>
          ))}
        </Box>
      </Paper>
    </Box>
  )
}
