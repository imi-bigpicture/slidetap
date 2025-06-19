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

import HomeIcon from '@mui/icons-material/Home'
import { Breadcrumbs, Link } from '@mui/material'
import Grid from '@mui/material/Grid'

import React from 'react'
import DisplayAttribute from 'src/components/attribute/display_attribute'
import type { ItemDetailAction } from 'src/models/action'
import { AttributeValueTypes, type Attribute } from 'src/models/attribute'
import { AttributeSchema } from 'src/models/schema/attribute_schema'

interface NestedAttributeDetailsProps {
  openedAttributes: Array<{
    schema: AttributeSchema
    attribute: Attribute<AttributeValueTypes>
    updateAttribute: (
      tag: string,
      attribute: Attribute<AttributeValueTypes>,
    ) => Attribute<AttributeValueTypes>
  }>
  action: ItemDetailAction
  handleNestedAttributeChange: (uid?: string) => void
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
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

export default function NestedAttributeDetails({
  openedAttributes,
  action,
  handleNestedAttributeChange,
  handleAttributeOpen,
  handleAttributeUpdate,
}: NestedAttributeDetailsProps): React.ReactElement {
  const handleNestedAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    openedAttributes.slice(-1).forEach((item) => {
      attribute = item.updateAttribute(tag, attribute)
    })
    handleAttributeUpdate(tag, attribute)
  }
  const attributeToDisplay = openedAttributes.slice(-1)[0]
  return (
    <Grid>
      <Breadcrumbs aria-label="breadcrumb">
        <Link
          onClick={() => {
            handleNestedAttributeChange()
          }}
        >
          <HomeIcon />
        </Link>
        {openedAttributes.map((item) => {
          return (
            <Link
              key={item.attribute.uid}
              onClick={() => {
                handleNestedAttributeChange(item.attribute.uid)
              }}
            >
              {item.schema.displayName}
            </Link>
          )
        })}
      </Breadcrumbs>
      <DisplayAttribute
        attribute={attributeToDisplay.attribute}
        schema={attributeToDisplay.schema}
        action={action}
        displayAsRoot={true}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleNestedAttributeUpdate}
      />
    </Grid>
  )
}
