import React from 'react'

import { Button, Tooltip } from '@mui/material'
import type { Attribute } from 'models/attribute'
import { ValueStatus } from 'models/status'

interface MappingButtonProps {
  attribute: Attribute<any, any>
}

export default function MappingButton({
  attribute,
}: MappingButtonProps): React.ReactElement {
  let color: 'error' | 'success' | 'warning' | 'info' = 'error'
  let tooltip = ''
  const mappingStatus = attribute.mappingStatus
  if (mappingStatus === ValueStatus.ORIGINAL_VALUE) {
    return <></>
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
      <Button size="small" color={color}>
        M
      </Button>
    </Tooltip>
  )
}
