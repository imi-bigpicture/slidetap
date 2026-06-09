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
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogContentText from '@mui/material/DialogContentText'
import DialogTitle from '@mui/material/DialogTitle'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState, type ReactElement } from 'react'
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
  const [pendingDelete, setPendingDelete] = useState<Project | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const projectsQuery = useQuery({
    queryKey: queryKeys.project.list(),
    queryFn: async () => {
      return await projectApi.getProjects()
    },
    refetchInterval: (query) => {
      const projects = query.state.data ?? []
      return projects.some(
        (p) => p.status === ProjectStatus.IN_PROGRESS || p.status === ProjectStatus.EXPORTING,
      )
        ? 2000
        : false
    },
    placeholderData: keepPreviousData,
  })

  const handleViewProject = (project: Project): void => {
    navigate(`/project/${project.uid}`)
  }

  const confirmDeleteProject = (): void => {
    if (pendingDelete === null) return
    const project = pendingDelete
    setIsDeleting(true)
    projectApi
      .delete(project.uid)
      .then(() => {
        projectsQuery.refetch()
      })
      .catch((error) => {
        showError('Failed to delete project', error)
      })
      .finally(() => {
        setIsDeleting(false)
        setPendingDelete(null)
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
    <>
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
          { action: Action.DELETE, onAction: setPendingDelete },
        ]}
        topBarActions={[
          <Button key="new" onClick={handleCreateProject}>
            New project
          </Button>,
        ]}
      />
      <Dialog
        open={pendingDelete !== null}
        onClose={() => {
          if (!isDeleting) setPendingDelete(null)
        }}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle>Delete project?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to delete <strong>{pendingDelete?.name}</strong>?
            This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingDelete(null)} disabled={isDeleting}>
            Cancel
          </Button>
          <Button
            onClick={confirmDeleteProject}
            color="error"
            variant="contained"
            disabled={isDeleting}
          >
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  )
}

export default ListProjects
