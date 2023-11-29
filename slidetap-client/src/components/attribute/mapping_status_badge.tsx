import React from 'react'

import { Badge, Tooltip } from '@mui/material'
import { ValueStatus } from 'models/status'
import type { Attribute } from 'models/attribute'

interface ValueStatusBadgeProps {
  attribute: Attribute<any, any>
}

export default function ValueStatusBadge({
  attribute,
}: ValueStatusBadgeProps): React.ReactElement {
  let color: 'error' | 'success' | 'warning' | 'info' = 'error'
  let tooltip = ''
  const mappingStatus = attribute.mappingStatus
  if (mappingStatus === ValueStatus.ORIGINAL_VALUE) {
    return <div>{attribute.schema.displayName}</div>
  } else if (mappingStatus === ValueStatus.UPDATED_VALUE) {
    color = 'info'
    tooltip = 'The attribute has an updated value'
  } else if (mappingStatus === ValueStatus.NO_MAPPABLE_VALUE) {
    color = 'error'
    tooltip = 'The attribute has no mappable value'
  } else if (mappingStatus === ValueStatus.NO_MAPPER) {
    color = 'warning'
    tooltip = 'The attribute has a mappable value but no mapper can map its type'
  } else if (mappingStatus === ValueStatus.NOT_MAPPED) {
    color = 'warning'
    tooltip = 'The attribute has a mappable value but no mapper can map the value'
  } else if (mappingStatus === ValueStatus.MAPPED) {
    color = 'success'
    tooltip = 'The attribute has a mapped value'
  }
  return (
    <Tooltip title={tooltip}>
      <Badge variant="dot" color={color}>
        {attribute.schema.displayName}
      </Badge>
    </Tooltip>
  )
}
