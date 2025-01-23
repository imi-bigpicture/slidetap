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

import { Stack, Typography } from '@mui/material'
import React from 'react'
import type { ProjectValidation } from 'src/models/validation'

interface DisplayProjectValidationProps {
  validation: ProjectValidation
}

export default function DisplayProjectValidation({
  validation,
}: DisplayProjectValidationProps): React.ReactElement {
  return (
    <Stack spacing={1} direction="column">
      {validation.nonValidAttributes.length !== 0 && (
        <Stack spacing={1} direction="column">
          <Typography variant="h6">Non valid attributes</Typography>
          {validation.nonValidAttributes.map((attribute) => attribute)}
        </Stack>
      )}
    </Stack>
  )
}
