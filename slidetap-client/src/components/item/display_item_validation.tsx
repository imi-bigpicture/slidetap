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

import { Stack, TextField, Typography } from '@mui/material'
import DisplayAttributeValidation from 'components/attribute/display_attribute_validation'
import type { ItemValidation, RelationValidation } from 'models/validation'
import React from 'react'

interface DisplayItemValidationProps {
  validation: ItemValidation
}

export default function DisplayItemValidation({
  validation,
}: DisplayItemValidationProps): React.ReactElement {
  return (
    <Stack spacing={2} direction="column">
      <TextField
        label="Name"
        defaultValue={validation.displayName}
        InputProps={{ readOnly: true }}
      />
      <TextField
        label="Valid"
        defaultValue={validation.valid}
        InputProps={{ readOnly: true }}
      />
      {validation.nonValidAttributes.length !== 0 && (
        <Stack spacing={2} direction="column">
          <Typography variant="h6">Non valid attributes</Typography>
          {validation.nonValidAttributes.map((attribute) => (
            <DisplayAttributeValidation
              key={attribute.uid}
              validation={attribute}
            ></DisplayAttributeValidation>
          ))}
        </Stack>
      )}
      {validation.nonValidRelations.length !== 0 && (
        <Stack spacing={2} direction="column">
          <Typography variant="h6">Non valid relations</Typography>
          {validation.nonValidRelations.map((relation) => (
            <DisplayRelationValidation
              key={relation.uid}
              validation={relation}
            ></DisplayRelationValidation>
          ))}
        </Stack>
      )}
    </Stack>
  )
}

interface DisplayRelationValidationProps {
  validation: RelationValidation
}

function DisplayRelationValidation({
  validation,
}: DisplayRelationValidationProps): React.ReactElement {
  return (
    <Stack spacing={2} direction="row">
      <TextField
        label="Name"
        defaultValue={validation.displayName}
        InputProps={{ readOnly: true }}
      />
      <TextField
        label="Valid"
        defaultValue={validation.valid}
        InputProps={{ readOnly: true }}
      />
    </Stack>
  )
}
