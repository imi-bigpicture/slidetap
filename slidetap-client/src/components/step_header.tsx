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

interface StepHeaderProps {
  title: string
  description?: string
  instructions?: string
}

export default function StepHeader({
  title,
  description,
  instructions,
}: StepHeaderProps): React.ReactElement {
  return (
    <Stack alignItems="flex-start" justifyContent="flex-start" direction={'row'}>
      <Typography variant="h5">{title}</Typography>
      <span />
      {description !== undefined && <Typography variant="h6">{description}</Typography>}
      {instructions !== undefined && (
        <Typography variant="subtitle1">{instructions}</Typography>
      )}
    </Stack>
  )
}
