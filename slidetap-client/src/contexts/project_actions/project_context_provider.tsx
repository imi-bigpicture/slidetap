//    Copyright 2026 SECTRA AB
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

import LinearProgress from '@mui/material/LinearProgress'
import { useQuery } from '@tanstack/react-query'
import React from 'react'
import { SchemaContextProvider } from 'src/contexts/schema/schema_context_provider'
import projectApi from 'src/services/api/project_api'
import { queryKeys } from 'src/services/query_keys'
import { ProjectActionsContext } from './project_actions_context'

/** Provides what is shown of a project with the root schema the project is on,
 * and with the actions the project can be offered.
 *
 * A project stays on the root it was created with, which need not be the root
 * of new projects, and a project on a view-only root is only shown. */
export const ProjectContextProvider = ({
  projectUid,
  children,
}: {
  projectUid: string
  children: React.ReactNode
}) => {
  const projectQuery = useQuery({
    queryKey: queryKeys.project.detail(projectUid),
    queryFn: async () => {
      return await projectApi.get(projectUid)
    },
  })
  const actionsQuery = useQuery({
    queryKey: queryKeys.project.actions(projectUid),
    queryFn: async () => {
      return await projectApi.getActions(projectUid)
    },
  })

  if (projectQuery.isError) {
    throw projectQuery.error
  }
  if (actionsQuery.isError) {
    throw actionsQuery.error
  }
  if (projectQuery.data === undefined || actionsQuery.data === undefined) {
    return <LinearProgress />
  }

  return (
    <SchemaContextProvider rootSchemaUid={projectQuery.data.rootSchemaUid}>
      <ProjectActionsContext.Provider value={actionsQuery.data}>
        {children}
      </ProjectActionsContext.Provider>
    </SchemaContextProvider>
  )
}
