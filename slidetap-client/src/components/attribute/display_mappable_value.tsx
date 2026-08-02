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

import { Stack, TextField } from '@mui/material'
import React from 'react'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import DisplayAttributeMapping from './display_attribute_mapping'

/** The raw string a mapping is attempted from, with the mapping it produced.
 *
 * The mappable value is always a string, whatever the attribute type, so it
 * gets its own field rather than going through the typed value components.
 */
export default function DisplayMappableValue({
  attribute,
}: {
  attribute: Attribute<AttributeValueTypes>
}): React.ReactElement {
  return (
    <Stack spacing={1} sx={{ width: '100%' }}>
      <TextField
        label="Mappable value"
        size="small"
        fullWidth
        value={attribute.mappableValue ?? ''}
        slotProps={{
          input: { readOnly: true },
          inputLabel: { shrink: true },
        }}
      />
      <DisplayAttributeMapping attribute={attribute} />
    </Stack>
  )
}
