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
