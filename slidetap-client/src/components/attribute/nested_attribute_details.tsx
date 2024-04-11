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
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import DisplayAttribute from 'components/attribute/display_attribute'
import type { Action } from 'models/action'
import { type Attribute } from 'models/attribute'
import React from 'react'

interface NestedAttributeDetailsProps {
  openedAttributes: Array<{
    attribute: Attribute<any, any>
    updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>
  }>
  action: Action
  handleNestedAttributeChange: (uid?: string) => void
  /** Handle adding new attribute to display open and display as nested attributes.
   * When an attribute should be opened, the attribute and a function for updating
   * the attribute in the parent attribute should be added.
   * @param attribute - Attribute to open
   * @param updateAttribute - Function to update the attribute in the parent attribute
   */
  handleAttributeOpen: (
    attribute: Attribute<any, any>,
    updateAttribute: (attribute: Attribute<any, any>) => Attribute<any, any>,
  ) => void
  handleAttributeUpdate: (attribute: Attribute<any, any>) => void
}

export default function NestedAttributeDetails({
  openedAttributes,
  action,
  handleNestedAttributeChange,
  handleAttributeOpen,
  handleAttributeUpdate,
}: NestedAttributeDetailsProps): React.ReactElement {
  const handleNestedAttributeUpdate = (attribute: Attribute<any, any>): void => {
    openedAttributes.slice(-1).forEach((item) => {
      attribute = item.updateAttribute(attribute)
    })
    handleAttributeUpdate(attribute)
  }
  const attributeToDisplay = openedAttributes.slice(-1)[0].attribute
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
              {item.attribute.schema.displayName}
            </Link>
          )
        })}
      </Breadcrumbs>
      <DisplayAttribute
        attribute={attributeToDisplay}
        action={action}
        displayAsRoot={true}
        handleAttributeOpen={handleAttributeOpen}
        handleAttributeUpdate={handleNestedAttributeUpdate}
      />
    </Grid>
  )
}
