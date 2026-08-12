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

import React, { useState } from 'react'

import { ExpandLess, ExpandMore } from '@mui/icons-material'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Collapse from '@mui/material/Collapse'
import Grid from '@mui/material/Grid'
import Typography from '@mui/material/Typography'
import DisplayAttribute from 'src/components/attribute/display_attribute'
import { isListAttributeSchema, isStringAttributeSchema } from 'src/models/helpers'
import type { ItemDetailAction } from 'src/models/action'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import {
  AttributeDisplay,
  AttributeGroupLayout,
  AttributeSchema,
  isShown,
} from 'src/models/schema/attribute_schema'
import { getContainerSpanSx } from 'src/components/container_span'

interface AttributeDetailsProps {
  schemas: Record<string, AttributeSchema>
  attributes: Record<string, Attribute<AttributeValueTypes>> | null
  action: ItemDetailAction
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  attributeLayout?: AttributeGroupLayout[]
  /** Tags whose attributes should render collapsed initially behind a toggle. */
  defaultCollapsed?: string[]
  spacing?: number
  marginTop?: number
  handleAttributeOpen: (
    schema: AttributeSchema,
    attribute: Attribute<AttributeValueTypes>,
    updateAttribute: (
      tag: string,
      attribute: Attribute<AttributeValueTypes>,
    ) => Attribute<AttributeValueTypes>,
  ) => void
  handleAttributeUpdate: (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ) => void
  /** Optional wrapper rendered around each top-level attribute. Lets callers
   * decorate individual attributes (e.g. with a drag handle) without
   * embedding feature-specific UI in this component. */
  renderAttributeContent?: (
    tag: string,
    content: React.ReactElement,
  ) => React.ReactElement
  /** Passed to each attribute: whether the raw/mapped/original value picker is
   * shown beside it. */
  showValueControls?: boolean
  /** Long texts divide the height available instead of growing to their
   * content, each scrolling within its share. */
  fillHeight?: boolean
}

/** Whether the value can fold itself away behind its own label: it has one,
 * and it is long enough to be worth closing. */
function foldable(schema: AttributeSchema): boolean {
  return (
    (isStringAttributeSchema(schema) && schema.multiline) ||
    isListAttributeSchema(schema)
  )
}

/** A header that folds its content away. Used where the content cannot carry
 * the toggle itself — a group of attributes, or a value that has no label of
 * its own to put a chevron on. */
function CollapsibleAttribute({
  label,
  open,
  onToggle,
  children,
}: {
  label: string
  /** Controlled by the parent, which needs to know whether this is expanded to
   * decide if it takes a share of the height. */
  open: boolean
  onToggle: () => void
  children: React.ReactNode
}): React.ReactElement {
  return (
    // Spaced and lettered like a closed text field, which is what it sits
    // among: a value folded away is a name and a rule either way, and one of
    // them shouting in primary reads as the only thing worth clicking.
    <Box sx={{ my: 1 }}>
      <Button
        size="small"
        color="inherit"
        onClick={onToggle}
        startIcon={open ? <ExpandLess /> : <ExpandMore />}
        sx={{
          textTransform: 'none',
          justifyContent: 'flex-start',
          color: 'text.secondary',
          borderTop: 1,
          borderColor: 'divider',
          borderRadius: 0,
          typography: 'caption',
          px: 0.5,
        }}
        fullWidth
      >
        {label}
      </Button>
      <Collapse in={open} unmountOnExit>
        <Box sx={{ mt: 1 }}>{children}</Box>
      </Collapse>
    </Box>
  )
}

export default function AttributeDetails({
  schemas,
  attributes,
  action,
  attributeLayout,
  defaultCollapsed,
  spacing,
  marginTop,
  handleAttributeOpen,
  handleAttributeUpdate,
  renderAttributeContent,
  showValueControls = true,
  fillHeight = false,
}: AttributeDetailsProps): React.ReactElement {
  if (spacing === undefined) {
    spacing = 2
  }

  const collapsedSet = React.useMemo(
    () => new Set(defaultCollapsed ?? []),
    [defaultCollapsed],
  )
  // Which collapsible attributes are open, held here rather than inside each
  // one: whether an attribute is expanded decides whether it takes a share of
  // the height, and that is settled where the shares are handed out. Open to
  // start with unless the layout said otherwise.
  const [expandedTags, setExpandedTags] = useState<Set<string>>(
    () =>
      new Set(
        Object.values(schemas)
          .filter((schema) => foldable(schema) && !collapsedSet.has(schema.tag))
          .map((schema) => schema.tag),
      ),
  )
  const toggleExpanded = (tag: string): void => {
    setExpandedTags((previous) => {
      const next = new Set(previous)
      if (next.has(tag)) {
        next.delete(tag)
      } else {
        next.add(tag)
      }
      return next
    })
  }

  /** Widths a group asks for assume the whole cell is the field. Where the
   * value picker sits beside it there is a chip's worth less room in every
   * cell, and six of them across a row leaves a checkbox with its label wrapped
   * over three lines. Two per row is as narrow as that stays readable, so the
   * declared widths still order and pair the fields — the same layout the
   * overview reads — but nothing is squeezed past half a row. */
  const widenForControls = (
    width: Record<string, number>,
  ): Record<string, number> => {
    if (!showValueControls) return width
    return Object.fromEntries(
      Object.entries(width).map(([breakpoint, span]) => [
        breakpoint,
        Math.max(span, 6),
      ]),
    )
  }

  const createAttribute = (schema: AttributeSchema): Attribute<AttributeValueTypes> => {
    return {
      uid: '00000000-0000-0000-0000-000000000000',
      displayValue: '',
      valid: schema.optional,
      schemaUid: schema.uid,
      attributeValueType: schema.attributeValueType,
      originalValue: null,
      updatedValue: null,
      mappedValue: null,
      mappableValue: null,
      mappingItemUid: null,
    }
  }

  const renderAttribute = (
    schema: AttributeSchema,
    displayWidth: Record<string, number>,
    /** Lay out against the width of the group rather than of the window. */
    inContainerGrid = false,
  ) => {
    if (!isShown(schema, AttributeDisplay.Details)) return null
    const attribute = attributes?.[schema.tag] ?? createAttribute(schema)
    // Anything that can fold does, whether or not the layout asked for it to
    // start folded: a panel where one long text has a chevron and the next
    // does not reads as an accident, and the layout is choosing what is open
    // rather than what can close.
    const togglesOnLabel = foldable(schema)
    const expanded = expandedTags.has(schema.tag)
    // Only the texts behind a toggle give way, and only while open. One that is
    // always shown is there because it is always wanted, so it keeps the height
    // its content needs and the ones the reader opened take what is left.
    const fills = fillHeight && togglesOnLabel && expanded
    const inner = (
      <DisplayAttribute
        attribute={attribute}
        schema={schema}
        action={action}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleAttributeUpdate}
        showValueControls={showValueControls}
        fillHeight={fills}
        collapse={
          togglesOnLabel
            ? { open: expanded, onToggle: () => toggleExpanded(schema.tag) }
            : undefined
        }
      />
    )
    // A field that folds itself needs no header: it keeps its outline and its
    // name either way, so nothing has to stand in for it while it is closed.
    const wrapped =
      collapsedSet.has(schema.tag) && !togglesOnLabel ? (
        <CollapsibleAttribute
          label={schema.displayName}
          open={expanded}
          onToggle={() => toggleExpanded(schema.tag)}
        >
          {inner}
        </CollapsibleAttribute>
      ) : (
        inner
      )
    const decorated = renderAttributeContent
      ? renderAttributeContent(schema.tag, wrapped)
      : wrapped
    // Grid lays out in a row with its own basis and negative margins, which
    // cannot be turned into a height-sharing column without the items landing
    // on top of each other. A plain flex column instead.
    if (fillHeight) {
      return (
        <Box
          key={schema.uid}
          // Even shares, but none taller than its text: flex hands out the
          // height equally, clamps whoever asks for less than its share, and
          // gives what that frees to the rest. So two long texts split the
          // panel down the middle, and a short one beside a long one takes
          // only its few lines and leaves the long one the remainder.
          sx={
            fills
              ? { flex: '1 1 0', minHeight: 0, maxHeight: 'max-content' }
              : { flexShrink: 0 }
          }
        >
          {decorated}
        </Box>
      )
    }
    if (inContainerGrid) {
      return (
        <Box key={schema.uid} sx={getContainerSpanSx(displayWidth, false)}>
          {decorated}
        </Box>
      )
    }
    return (
      <Grid key={schema.uid} size={displayWidth}>
        {decorated}
      </Grid>
    )
  }

  const renderGroupAttributes = (group: AttributeGroupLayout) => {
    return Object.entries(group.attributes).map(([tag, settings]) => {
      const schema = schemas[tag]
      if (schema === undefined) return null
      const displayWidth =
        group.direction === 'column' ? { xs: 12 } : widenForControls(settings.width)
      return renderAttribute(schema, displayWidth, true)
    })
  }

  /** Six checkboxes fit on one row in a wide card and want two or three rows in
   * a narrow one — which is a question about the card, not about the window a
   * Grid breakpoint would answer. */
  const groupGrid = (children: React.ReactNode): React.ReactElement => (
    <Box
      sx={{
        display: 'grid',
        gridTemplateColumns: 'repeat(12, 1fr)',
        gap: spacing,
        containerType: 'inline-size',
      }}
    >
      {children}
    </Box>
  )

  // If no layout defined, render all schemas with width 12
  if (attributeLayout === undefined || attributeLayout.length === 0) {
    if (fillHeight) {
      return (
        <Box
          sx={{
            marginTop: marginTop,
            width: '100%',
            height: '100%',
            minHeight: 0,
            display: 'flex',
            flexDirection: 'column',
            // Wider than elsewhere: a box that has been shrunk ends mid-text at
            // its border, so the next field's label needs clear air above it to
            // read as a separate field rather than a continuation.
            gap: spacing + 1,
          }}
        >
          {Object.values(schemas).map((schema) => renderAttribute(schema, { xs: 12 }))}
        </Box>
      )
    }
    return (
      <Grid container spacing={spacing} sx={{ marginTop: marginTop, width: '100%' }}>
        {Object.values(schemas).map((schema) => renderAttribute(schema, { xs: 12 }))}
      </Grid>
    )
  }

  // Collect tags that are in any group
  const laidOutTags = new Set<string>()
  for (const group of attributeLayout) {
    for (const tag of Object.keys(group.attributes)) {
      laidOutTags.add(tag)
    }
  }

  return (
    <Grid container spacing={spacing} sx={{ marginTop: marginTop, width: '100%' }}>
      <Grid size={{ xs: 12 }}>
        <Box
          sx={{
            display: 'grid',
            gridTemplateColumns: 'repeat(12, 1fr)',
            gap: spacing,
            containerType: 'inline-size',
          }}
        >
          {attributeLayout.map((group, groupIndex) => (
            <Box key={groupIndex} sx={getContainerSpanSx(group.width, group.expand)}>
              {/* A named group can fold behind its name, so detail is at hand
                  without costing height while scanning several items. */}
              {group.collapsed && group.name !== null ? (
                <CollapsibleAttribute
                  label={group.name}
                  open={expandedTags.has(group.name)}
                  onToggle={() => toggleExpanded(group.name as string)}
                >
                  {groupGrid(renderGroupAttributes(group))}
                </CollapsibleAttribute>
              ) : (
                <React.Fragment>
                  {group.name !== null && (
                    <Typography variant="subtitle2" sx={{ mb: 1 }}>
                      {group.name}
                    </Typography>
                  )}
                  {groupGrid(renderGroupAttributes(group))}
                </React.Fragment>
              )}
            </Box>
          ))}
        </Box>
      </Grid>
      {/* Render attributes not in any group at the end with width 12 */}
      {Object.values(schemas)
        .filter((schema) => !laidOutTags.has(schema.tag))
        .map((schema) => renderAttribute(schema, { xs: 12 }))}
    </Grid>
  )
}
