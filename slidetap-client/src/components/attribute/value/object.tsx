import React from 'react'
import type { Attribute, ObjectAttribute } from 'models/attribute'
import DisplayAttribute from '../display_attribute'
import Grid from '@mui/material/Unstable_Grid2' // Grid version 2
import type { Action } from 'models/table_item'

interface DisplayObjectAttributeProps {
  attribute: ObjectAttribute
  action: Action
  handleAttributeOpen?: (attribute: Attribute<any, any>) => void
  handleAttributeUpdate?: (attribute: ObjectAttribute) => void
}

export default function DisplayObjectAttribute({
  attribute,
  action,
  handleAttributeOpen,
  handleAttributeUpdate,
}: DisplayObjectAttributeProps): React.ReactElement {
  let handleOwnAttributeUpdate: ((attribute: Attribute<any, any>) => void) | undefined
  if (handleAttributeUpdate !== undefined) {
    handleOwnAttributeUpdate = (updatedAttribute: Attribute<any, any>): void => {
      const updated = { ...attribute }
      if (updated.value === undefined) {
        updated.value = {}
      }
      updated.value[updatedAttribute.schema.tag] = updatedAttribute
      handleAttributeUpdate(updated)
    }
  }
  return (
    <React.Fragment>
      {attribute.value !== undefined &&
        Object.values(attribute.value).map((childAttribute) => {
          return (
            <Grid key={childAttribute.uid}>
              <DisplayAttribute
                key={childAttribute.uid}
                action={action}
                attribute={childAttribute}
                hideLabel={false}
                handleAttributeOpen={handleAttributeOpen}
                handleAttributeUpdate={handleOwnAttributeUpdate}
                complexAttributeAsButton={true}
              />
            </Grid>
          )
        })}
    </React.Fragment>
  )
}
