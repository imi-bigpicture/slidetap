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

import Button from '@mui/material/Button'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import { BasicTable } from 'src/components/table/basic_table'
import { useError } from 'src/contexts/error/error_context'
import { Action } from 'src/models/action'
import { Project } from 'src/models/project'
import {
  ProjectStatus,
  ProjectStatusList,
  ProjectStatusStrings,
} from 'src/models/project_status'
import projectApi from 'src/services/api/project_api'
import { queryKeys } from 'src/services/query_keys'
import StatusChip from '../status_chip'

function ListProjects(): ReactElement {
  const navigate = useNavigate()
  const { showError } = useError()
  const projectsQuery = useQuery({
    queryKey: queryKeys.project.list(),
    queryFn: async () => {
      return await projectApi.getProjects()
    },
    refetchInterval: 2000,
    placeholderData: keepPreviousData,
  })

  const handleViewProject = (project: Project): void => {
    navigate(`/project/${project.uid}`)
  }
  const handleDeleteProject = (project: Project): void => {
    projectApi
      .delete(project.uid)
      .then(() => {
        projectsQuery.refetch()
      })
      .catch((error) => {
        showError('Failed to delete project', error)
      })
  }

  const handleCreateProject = (): void => {
    projectApi
      .create('New project')
      .then((project) => {
        navigate('/project/' + project.uid + '/settings')
      })
      .catch((error) => {
        showError('Failed to create project', error)
      })
  }
  return (
    <BasicTable
      columns={[
        {
          header: 'Name',
          accessorKey: 'name',
        },
        {
          header: 'Created',
          accessorKey: 'created',
          Cell: ({ row }) => new Date(row.original.created).toLocaleString('en-gb'),
          filterVariant: 'date-range',
        },
        {
          header: 'Status',
          accessorKey: 'status',
          Cell: ({ row }) => (
            <StatusChip
              status={row.original.status}
              stringMap={ProjectStatusStrings}
              colorMap={{
                [ProjectStatus.IN_PROGRESS]: 'primary',
                [ProjectStatus.COMPLETED]: 'success',
                [ProjectStatus.EXPORTING]: 'primary',
                [ProjectStatus.EXPORT_COMPLETE]: 'success',
                [ProjectStatus.FAILED]: 'error',
                [ProjectStatus.DELETED]: 'secondary',
              }}
              onClick={() => handleViewProject(row.original)}
            />
          ),
          filterVariant: 'multi-select',
          filterSelectOptions: ProjectStatusList.map((status) => ({
            label: ProjectStatusStrings[status],
            value: status.toString(),
          })),
        },
      ]}
      data={projectsQuery.data ?? []}
      rowsSelectable={false}
      isLoading={projectsQuery.isLoading}
      actions={[
        { action: Action.VIEW, onAction: handleViewProject },
        { action: Action.DELETE, onAction: handleDeleteProject },
      ]}
      topBarActions={[
        <Button key="new" onClick={handleCreateProject}>
          New project
        </Button>,
      ]}
    />
  )
}

export default ListProjects
