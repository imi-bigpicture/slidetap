import React from 'react'

import { Badge, Tooltip } from '@mui/material'
import { MappingStatus } from 'models/status'
import type { Attribute } from 'models/attribute'

interface MappingStatusBadgeProps {
  attribute: Attribute<any, any>
}

export default function MappingStatusBadge({
  attribute,
}: MappingStatusBadgeProps): React.ReactElement {
  let color: 'error' | 'success' | 'warning' = 'error'
  let tooltip = ''
  const mappingStatus = attribute.mappingStatus
  if (mappingStatus === MappingStatus.ORIGINAL_VALUE) {
    return <div>{attribute.schema.displayName}</div>
  } else if (mappingStatus === MappingStatus.NO_MAPPABLE_VALUE) {
    color = 'error'
    tooltip = 'The attribute has no mappable value'
  } else if (mappingStatus === MappingStatus.NO_MAPPER) {
    color = 'warning'
    tooltip = 'The attribute has a mappable value but no mapper can map its type'
  } else if (mappingStatus === MappingStatus.NOT_MAPPED) {
    color = 'warning'
    tooltip = 'The attribute has a mappable value but no mapper can map the value'
  } else if (mappingStatus === MappingStatus.MAPPED) {
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
