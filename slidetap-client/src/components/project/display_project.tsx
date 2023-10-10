import React, { useEffect, useState, type ReactElement } from 'react'
import { Route, useNavigate } from 'react-router-dom'
import Search from 'components/project/setup/search'
import type { Project } from 'models/project'
import { ProjectStatus, ProjectStatusStrings } from 'models/status'
import Settings from 'components/project/settings'
import Batches from 'components/project/batches'
import projectApi from 'services/api/project_api'
import Curate from 'components/project/setup/curate'
import Overview from 'components/project/overview'
import SideBar, { type MenuSection } from 'components/side_bar'
import Progress from 'components/project/export/progress'
import Validate from 'components/project/export/validate/validate'
import Submit from 'components/project/export/submit'
import Execute from 'components/project/export/execute'

const newProject = {
  uid: '',
  name: 'New project',
  status: ProjectStatus.NOT_STARTED,
  itemSchemas: [],
  itemCounts: [],
}

export default function DisplayProject(): ReactElement {
  const [project, setProject] = useState<Project>(newProject)
  const [view, setView] = useState<string>('')
  // const parameters = useParams()
  const navigate = useNavigate()
  const projectUid = window.location.pathname.split('project/').pop()?.split('/')[0]
  function changeView(view: string): void {
    setView(view)
    navigate(view)
  }

  function projectIsSearchable(project: Project): boolean {
    return (
      project.uid !== '' &&
      (project.status === ProjectStatus.NOT_STARTED || projectIsEditable(project))
    )
  }

  function projectIsEditable(project: Project): boolean {
    return (
      project.status === ProjectStatus.SEARCHING ||
      project.status === ProjectStatus.SEARCH_COMPLETE
    )
  }

  function projectIsStartable(project: Project): boolean {
    return project.status === ProjectStatus.SEARCH_COMPLETE
  }

  function projectIsConverting(project: Project): boolean {
    return project.status >= ProjectStatus.STARTED
  }

  function projectIsCompleted(project: Project): boolean {
    return project.status === ProjectStatus.COMPLETED
  }

  useEffect(() => {
    const getProject = (): void => {
      if (projectUid === undefined || projectUid === '') {
        setProject(newProject)
      } else {
        projectApi
          .get(projectUid)
          .then((project) => {setProject(project)})
          .catch((x) => {console.error('Failed to get project', x)})
      }
    }
    getProject()
    const intervalId = setInterval(() => {
        getProject()
    }, 2000)
    return () => {clearInterval(intervalId)}
  }, [projectUid])
  const projectSection: MenuSection = {
    name: 'Project: ' + project.name,
    description: ProjectStatusStrings[project.status],
    items: [
      { name: 'Overview', path: '' },
      { name: 'Settings', path: 'settings' },
      // {name: "Batch", path: "batches", disabled: (project.id === undefined)}
    ],
  }

  const setupSection: MenuSection = {
    name: 'Setup',
    items: [
      {
        name: 'Search',
        path: 'search',
        disabled: !projectIsSearchable(project),
      },
      { name: 'Curate', path: 'curate', disabled: !projectIsEditable(project) },
    ],
  }

  const convertSection: MenuSection = {
    name: 'Export',
    items: [
      {
        name: 'Execute',
        path: 'execute',
        disabled: !projectIsStartable(project),
      },
      {
        name: 'Progress',
        path: 'progress',
        disabled: !projectIsConverting(project),
      },
      {
        name: 'Validate',
        path: 'validate',
        disabled: !projectIsConverting(project),
      },
      {
        name: 'Submit',
        path: 'submit',
        disabled: !projectIsCompleted(project),
      },
    ],
  }
  const sections = [projectSection, setupSection, convertSection]
  const routes = [
    <Route key="overview" path="/" element={<Overview project={project} />} />,
    <Route
      key="settings"
      path="/settings"
      element={<Settings project={project} setProject={setProject} />}
    />,
    <Route key="batches" path="/batches" element={<Batches project={project} />} />,
    <Route
      key="search"
      path="/search"
      element={<Search project={project} nextView="curate" changeView={changeView} />}
    />,
    <Route
      key="curate"
      path="/curate"
      element={project.uid !== '' && <Curate project={project} />}
    />,
    <Route
      key="execute"
      path="/execute"
      element={
        project.uid !== '' && (
          <Execute project={project} nextView="progress" changeView={changeView} />
        )
      }
    />,
    <Route
      key="progress"
      path="/progress"
      element={project.uid !== '' && <Progress project={project} />}
    />,
    <Route
      key="validate"
      path="/validate"
      element={project.uid !== '' && <Validate project={project} />}
    />,
    <Route
      key="submit"
      path="/submit"
      element={project.uid !== '' && <Submit project={project} />}
    />,
  ]
  return (
    <SideBar
      sections={sections}
      routes={routes}
      selectedView={view}
      changeView={changeView}
    />
  )
}
