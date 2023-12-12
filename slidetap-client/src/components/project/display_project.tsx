import React, { useEffect, useState, type ReactElement } from 'react'
import { Route, useNavigate } from 'react-router-dom'
import Search from 'components/project/search'
import type { Project } from 'models/project'
import { ProjectStatus, ProjectStatusStrings } from 'models/status'
import Settings from 'components/project/settings'
import Batches from 'components/project/batches'
import projectApi from 'services/api/project_api'
import Curate from 'components/project/curate'
import Overview from 'components/project/overview'
import SideBar, { type MenuSection } from 'components/side_bar'
import Progress from 'components/project/progress'
import Validate from 'components/project/validate/validate'
import Download from 'components/project/download'
import Export from 'components/project/submit'
import Process from 'components/project/process'

const newProject = {
  uid: '',
  name: 'New project',
  status: ProjectStatus.INITIALIZED,
  itemSchemas: [],
  itemCounts: [],
}

export default function DisplayProject(): ReactElement {
  const [project, setProject] = useState<Project>(newProject)
  const [view, setView] = useState<string>('')
  // const parameters = useParams()
  const navigate = useNavigate()
  const projectUid = window.location.pathname.split('project/').pop()?.split('/')[0]

  function projectIsSearchable(project: Project): boolean {
    return (
      project.uid !== '' &&
      (project.status === ProjectStatus.INITIALIZED ||
        projectIsMetadataEditable(project))
    )
  }

  function projectIsMetadataEditable(project: Project): boolean {
    return (
      project.status === ProjectStatus.METADATA_SEARCHING ||
      project.status === ProjectStatus.METEDATA_SEARCH_COMPLETE
    )
  }

  function projectIsDownloadable(project: Project): boolean {
    return project.status === ProjectStatus.METEDATA_SEARCH_COMPLETE
  }

  function projectIsImageEditable(project: Project): boolean {
    return (
      project.status === ProjectStatus.IMAGE_PRE_PROCESSING ||
      project.status === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
    )
  }

  function projectIsProcessable(project: Project): boolean {
    return project.status === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
  }

  function projectIsConverting(project: Project): boolean {
    return (
      project.status === ProjectStatus.IMAGE_POST_PROCESSING ||
      project.status === ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE
    )
  }

  function projectIsCompleted(project: Project): boolean {
    return (
      project.status === ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE ||
      project.status === ProjectStatus.EXPORTING ||
      project.status === ProjectStatus.EXPORT_COMPLETE
    )
  }
  const getProject = (): void => {
    if (projectUid === undefined || projectUid === '') {
      setProject(newProject)
    } else {
      projectApi
        .get(projectUid)
        .then((project) => {
          setProject(project)
        })
        .catch((x) => {
          console.error('Failed to get project', x)
        })
    }
  }

  useEffect(() => {
    getProject()
    // const intervalId = setInterval(() => {
    //   getProject()
    // }, 20000)
    return () => {
      // clearInterval(intervalId)
    }
  }, [projectUid])

  function changeView(view: string): void {
    setView(view)
    navigate(view)
    getProject()
  }
  const projectSection: MenuSection = {
    name: 'Project: ' + project.name,
    description: ProjectStatusStrings[project.status],
    items: [
      { name: 'Overview', path: '' },
      { name: 'Settings', path: 'settings' },
      // {name: "Batch", path: "batches", disabled: (project.id === undefined)}
    ],
  }

  const metadataSection: MenuSection = {
    name: 'Metadata',
    items: [
      {
        name: 'Search',
        path: 'search',
        disabled: !projectIsSearchable(project),
      },
      {
        name: 'Curate',
        path: 'curate_metadata',
        disabled: !projectIsMetadataEditable(project),
      },
    ],
  }

  const imageSection: MenuSection = {
    name: 'Image',
    items: [
      {
        name: 'Download',
        path: 'download',
        disabled: !projectIsDownloadable(project),
      },
      {
        name: 'Curate',
        path: 'curate_image',
        disabled: !projectIsImageEditable(project),
      },
    ],
  }

  const convertSection: MenuSection = {
    name: 'Export',
    items: [
      {
        name: 'Process',
        path: 'process',
        disabled: !projectIsProcessable(project),
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
        name: 'Export',
        path: 'export',
        disabled: !projectIsCompleted(project),
      },
    ],
  }

  const sections = [projectSection, metadataSection, imageSection, convertSection]
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
      element={
        <Search project={project} nextView="curate_metadata" changeView={changeView} />
      }
    />,
    <Route
      key="curateMetadata"
      path="/curate_metadata"
      element={project.uid !== '' && <Curate project={project} />}
    />,
    <Route
      key="download"
      path="/download"
      element={
        project.uid !== '' && (
          <Download project={project} nextView="curate_image" changeView={changeView} />
        )
      }
    />,
    <Route
      key="curateImage"
      path="/curate_image"
      element={project.uid !== '' && <Curate project={project} />}
    />,
    <Route
      key="process"
      path="/process"
      element={
        project.uid !== '' && (
          <Process project={project} nextView="progress" changeView={changeView} />
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
      key="export"
      path="/export"
      element={project.uid !== '' && <Export project={project} />}
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
