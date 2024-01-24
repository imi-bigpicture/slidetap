import { Button } from '@mui/material'
import type { Action } from 'models/action'
import type { Attribute, ObjectAttribute } from 'models/attribute'
import React from 'react'
import DisplayAttribute from '../display_attribute'

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  action: Action
  complexAttributeAsButton: boolean
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
  handleAttributeUpdate: (attribute: ObjectAttribute) => void
}

export default function DisplayObjectAttribute({
  attribute,
  action,
  complexAttributeAsButton,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayObjectAttributeProps): React.ReactElement {
  const handleOwnAttributeUpdate = (
    updatedAttribute: Attribute<any, any>,
  ): Attribute<any, any> => {
    const updated = { ...attribute }
    if (updated.value === undefined) {
      updated.value = {}
    }
    updated.value[updatedAttribute.schema.tag] = updatedAttribute
    return updated
  }
  const handleNestedAttributeUpdate = (attribute: Attribute<any, any>): void => {
    const updated = handleOwnAttributeUpdate(attribute)
    handleAttributeUpdate(updated)
  }

  if (complexAttributeAsButton) {
    return (
      <Button
        id={attribute.uid}
        onClick={() => {
          handleAttributeOpen(attribute, handleOwnAttributeUpdate)
        }}
      >
        {attribute.schema.displayName}
      </Button>
    )
  }
  return (
    <React.Fragment>
      {attribute.value !== undefined &&
        Object.values(attribute.value).map((childAttribute) => {
          return (
            <DisplayAttribute
              key={childAttribute.uid}
              action={action}
              attribute={childAttribute}
              handleAttributeOpen={handleAttributeOpen}
              handleAttributeUpdate={handleNestedAttributeUpdate}
              complexAttributeAsButton={true}
            />
          )
        })}
    </React.Fragment>
  )
}
