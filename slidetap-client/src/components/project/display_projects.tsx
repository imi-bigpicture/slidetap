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
import { BasicTable } from 'components/table'
import type { Action } from 'models/action'
import type { Project } from 'models/project'
import { ProjectStatusStrings } from 'models/status'
import React, { useEffect, useState, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import projectApi from 'services/api/project_api'

function DisplayProjects(): ReactElement {
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)
  const navigate = useNavigate()
  const getProjects = (): void => {
    projectApi
      .getProjects()
      .then((projects) => {
        setProjects(projects)
        setIsLoading(false)
      })
      .catch((x) => {
        console.error('Failed to get projects', x)
      })
  }

  useEffect(() => {
    getProjects()
    const intervalId = setInterval(() => {
      getProjects()
    }, 2000)
    return () => {
      clearInterval(intervalId)
    }
  }, [])

  const navigateToProject = (projectUid: string, action: Action): void => {
    navigate(`/project/${projectUid}`)
  }

  const handleCreateProject = (event: React.MouseEvent<HTMLElement>): void => {
    projectApi
      .create('New project')
      .then((project) => {
        navigate('/project/' + project.uid + '/settings')
      })
      .catch((x) => {
        console.error('Failed to get images', x)
      })
  }

  return (
    <React.Fragment>
      <Button onClick={handleCreateProject}>New project</Button>
      <BasicTable
        columns={[
          {
            header: 'Name',
            accessorKey: 'name',
          },
          {
            header: 'Status',
            accessorKey: 'status',
          },
        ]}
        data={projects.map((project) => {
          return {
            id: project.uid,
            uid: project.uid,
            name: project.name,
            status: ProjectStatusStrings[project.status],
          }
        })}
        rowsSelectable={false}
        onRowAction={navigateToProject}
        isLoading={isLoading}
      />
    </React.Fragment>
  )
}

export default DisplayProjects
