import React, { useEffect, useState, type ReactElement } from 'react'
import { useNavigate, NavLink } from 'react-router-dom'
import Button from '@mui/material/Button'
import type { Project } from 'models/project'
import projectApi from 'services/api/project_api'
import { Table } from 'components/table'
import { ProjectStatusStrings } from 'models/status'
import type { TableItem } from 'models/table_item'

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
      .catch((x) => {console.error('Failed to get projects', x)})
  }

  useEffect(() => {
    getProjects()
    const intervalId = setInterval(() => {
      getProjects()
    }, 2000)
    return () => {clearInterval(intervalId)}
  }, [])

  const navigateToProject = (project: TableItem): void => {
    navigate(`/project/${project.uid}`)
  }

  return (
    <React.Fragment>
      <Button component={NavLink} to="/project/new/settings">
        New project
      </Button>
      <Table
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
        onRowClick={navigateToProject}
        isLoading={isLoading}
      />
    </React.Fragment>
  )
}

export default DisplayProjects
