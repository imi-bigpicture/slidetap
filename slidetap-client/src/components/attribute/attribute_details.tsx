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

import Divider from '@mui/material/Divider'
import Grid from '@mui/material/Grid'
import DisplayAttribute from 'src/components/attribute/display_attribute'
import type { ItemDetailAction } from 'src/models/action'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import { AttributeGroupLayout, AttributeSchema } from 'src/models/schema/attribute_schema'

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
  attributeLayout?: Record<number, AttributeGroupLayout>
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

  const renderAttribute = (schema: AttributeSchema, displayWidth: number) => {
    const attribute = attributes?.[schema.tag] ?? createAttribute(schema)
    return (
      <Grid key={schema.uid} size={{ xs: displayWidth }}>
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

  // If no layout defined, render all schemas with width 12
  if (attributeLayout === undefined || Object.keys(attributeLayout).length === 0) {
    return (
      <Grid container spacing={spacing} sx={{ marginTop: marginTop, width: '100%' }}>
        {Object.values(schemas).map((schema) => renderAttribute(schema, 12))}
      </Grid>
    )
  }

  // Collect tags that are in any group
  const laidOutTags = new Set<string>()
  for (const group of Object.values(attributeLayout)) {
    for (const tag of Object.keys(group.attributes)) {
      laidOutTags.add(tag)
    }
  }

  // Sort groups by numeric key
  const sortedGroupKeys = Object.keys(attributeLayout)
    .map(Number)
    .sort((a, b) => a - b)

  return (
    <Grid container spacing={spacing} sx={{ marginTop: marginTop, width: '100%' }}>
      {sortedGroupKeys.map((groupKey) => {
        const group = attributeLayout[groupKey]
        return (
          <React.Fragment key={groupKey}>
            {group.name !== null && (
              <Grid size={{ xs: 12 }}>
                <Divider textAlign="left">{group.name}</Divider>
              </Grid>
            )}
            {Object.entries(group.attributes).map(([tag, settings]) => {
              const schema = schemas[tag]
              if (schema === undefined) return null
              return renderAttribute(schema, settings.displayWidth)
            })}
          </React.Fragment>
        )
      })}
      {/* Render attributes not in any group at the end with width 12 */}
      {Object.values(schemas)
        .filter((schema) => !laidOutTags.has(schema.tag))
        .map((schema) => renderAttribute(schema, 12))}
    </Grid>
  )
}
