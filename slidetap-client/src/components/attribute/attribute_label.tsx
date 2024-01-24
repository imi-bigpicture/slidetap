import { FormLabel } from '@mui/material'
import type { Attribute } from 'models/attribute'
import React from 'react'
import MappingButton from './mapping_status_button'

interface DisplayAttributeLabelProps {
  attribute: Attribute<any, any>
}

export default function DisplayAttributeLabel({
  attribute,
}: DisplayAttributeLabelProps): React.ReactElement {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}
    >
      <FormLabel component="legend">{attribute.schema.displayName}</FormLabel>
      <MappingButton attribute={attribute} />
    </div>
  )
}
