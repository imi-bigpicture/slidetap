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

import React from 'react'

import Box from '@mui/material/Box'
import Grid from '@mui/material/Grid'
import Typography from '@mui/material/Typography'
import DisplayAttribute from 'src/components/attribute/display_attribute'
import type { ItemDetailAction } from 'src/models/action'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import { type Breakpoint, AttributeGroupLayout, AttributeSchema } from 'src/models/schema/attribute_schema'

const containerBreakpoints: Record<string, number> = {
  sm: 400,
  md: 600,
  lg: 800,
  xl: 1024,
}

const getGroupSx = (
  width: Partial<Record<Breakpoint, number>>,
  expand: boolean,
): Record<string, any> => {
  if (expand) {
    return { gridColumn: '1 / -1' }
  }
  const sx: Record<string, any> = {
    gridColumn: `span ${width.xs ?? 12}`,
  }
  for (const [bp, span] of Object.entries(width)) {
    if (bp === 'xs') continue
    const minWidth = containerBreakpoints[bp]
    if (minWidth !== undefined) {
      sx[`@container (min-width: ${minWidth}px)`] = {
        gridColumn: `span ${span}`,
      }
    }
  }
  return sx
}

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
}

export default function AttributeDetails({
  schemas,
  attributes,
  action,
  attributeLayout,
  spacing,
  marginTop,
  handleAttributeOpen,
  handleAttributeUpdate,
}: AttributeDetailsProps): React.ReactElement {
  if (spacing === undefined) {
    spacing = 2
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

  const renderAttribute = (schema: AttributeSchema, displayWidth: Record<string, number>) => {
    const attribute = attributes?.[schema.tag] ?? createAttribute(schema)
    return (
      <Grid key={schema.uid} size={displayWidth}>
        <DisplayAttribute
          attribute={attribute}
          schema={schema}
          action={action}
          handleAttributeOpen={handleAttributeOpen}
          handleAttributeUpdate={handleAttributeUpdate}
        />
      </Grid>
    )
  }

  const renderGroupAttributes = (group: AttributeGroupLayout) => {
    return Object.entries(group.attributes).map(([tag, settings]) => {
      const schema = schemas[tag]
      if (schema === undefined) return null
      const displayWidth = group.direction === 'column' ? { xs: 12 } : settings.width
      return renderAttribute(schema, displayWidth)
    })
  }

  // If no layout defined, render all schemas with width 12
  if (attributeLayout === undefined || attributeLayout.length === 0) {
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
            <Box key={groupIndex} sx={getGroupSx(group.width, group.expand)}>
              {group.name !== null && (
                <Typography variant="subtitle2" sx={{ mb: 1 }}>{group.name}</Typography>
              )}
              <Grid container spacing={spacing}>
                {renderGroupAttributes(group)}
              </Grid>
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
