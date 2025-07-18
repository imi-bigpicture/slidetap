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

import { Box, Typography } from '@mui/material'
import React from 'react'
import Header from 'src/components/header'

export default function Title(): React.ReactElement {
  return (
    <React.Fragment>
      <Header />
      <Box margin={1}>
        <Typography variant="h4">Welcome to the SlideTap WebApp</Typography>
      </Box>
    </React.Fragment>
  )
}
