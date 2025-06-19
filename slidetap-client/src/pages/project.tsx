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

import React, { ReactElement } from 'react'
import { useParams } from 'react-router-dom'
import Header from 'src/components/header'
import DisplayProject from 'src/components/project/display_project'

export default function ProjectPage(): ReactElement {
  const { projectUid } = useParams()
  if (projectUid === undefined) {
    throw new Error('Project UID is required to display project page')
  }
  return (
    <React.Fragment>
      <Header />
      <DisplayProject projectUid={projectUid} />
    </React.Fragment>
  )
}
