import Batches from 'components/project/batches'
import Curate from 'components/project/curate'
import DownloadImages from 'components/project/download'
import Overview from 'components/project/overview'
import Process from 'components/project/process'
import Progress from 'components/project/progress'
import Search from 'components/project/search'
import Settings from 'components/project/settings'
import Export from 'components/project/submit'
import Validate from 'components/project/validate/validate'
import SideBar, { type MenuSection } from 'components/side_bar'
import type { Project } from 'models/project'
import { ProjectStatus, ProjectStatusStrings } from 'models/status'
import React, { useEffect, useState } from 'react'
import { Route, useNavigate } from 'react-router-dom'
import projectApi from 'services/api/project_api'

const newProject = {
  uid: '',
  name: 'New project',
  status: ProjectStatus.INITIALIZED,
  items: [],
}
function projectIsSearchable(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.INITIALIZED ||
    projectIsMetadataEditable(projectStatus)
  )
}

function projectIsMetadataEditable(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.METADATA_SEARCHING ||
    projectStatus === ProjectStatus.METEDATA_SEARCH_COMPLETE
  )
}

function projectIsDownloadable(projectStatus?: ProjectStatus): boolean {
  return projectStatus === ProjectStatus.METEDATA_SEARCH_COMPLETE
}

function projectIsImageEditable(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.IMAGE_PRE_PROCESSING ||
    projectStatus === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
  )
}

function projectIsProcessable(projectStatus?: ProjectStatus): boolean {
  return projectStatus === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
}

function projectIsConverting(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.IMAGE_POST_PROCESSING ||
    projectStatus === ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE
  )
}

function projectIsCompleted(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.IMAGE_POST_PROCESSING_COMPLETE ||
    projectStatus === ProjectStatus.EXPORTING ||
    projectStatus === ProjectStatus.EXPORT_COMPLETE
  )
}

export default function DisplayProject(): React.ReactElement {
  const [project, setProject] = useState<Project>(newProject)
  const [projectStatus, setProjectStatus] = useState<ProjectStatus>()
  const [view, setView] = useState<string>('')
  const navigate = useNavigate()
  const projectUid = window.location.pathname.split('project/').pop()?.split('/')[0]

  useEffect(() => {
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
    getProject()
  }, [projectUid])

  useEffect(() => {
    const getProjectStatus = (): void => {
      if (project?.uid === undefined || project?.uid === '') {
        return
      }
      projectApi
        .getStatus(project.uid)
        .then((status) => {
          setProjectStatus(status)
        })
        .catch((x) => {
          console.error('Failed to get project status', x)
        })
    }
    getProjectStatus()
    const intervalId = setInterval(() => {
      getProjectStatus()
    }, 5000)
    return () => {
      clearInterval(intervalId)
    }
  }, [project])

  function changeView(view: string): void {
    setView(view)
    navigate(view)
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

  const metadataSection = {
    name: 'Metadata',
    items: [
      {
        name: 'Search',
        path: 'search',
        enabled: projectIsSearchable(projectStatus),
      },
      {
        name: 'Curate',
        path: 'curate_metadata',
        enabled: projectIsMetadataEditable(projectStatus),
        hidden: !projectIsMetadataEditable(projectStatus),
      },
    ],
  }
  const imageSection = {
    name: 'Image',
    items: [
      {
        name: 'Download',
        path: 'download',
        enabled: projectIsDownloadable(projectStatus),
      },
      {
        name: 'Curate',
        path: 'curate_image',
        enabled: projectIsImageEditable(projectStatus),
        hidden: !projectIsImageEditable(projectStatus),
      },
    ],
  }
  const finalizeSection = {
    name: 'Finalize',
    items: [
      {
        name: 'Process',
        path: 'process',
        enabled: projectIsProcessable(projectStatus),
        hidden: projectIsConverting(projectStatus),
      },
      {
        name: 'Process',
        path: 'progress',
        enabled: projectIsConverting(projectStatus),
        hidden: !projectIsConverting(projectStatus),
      },
      {
        name: 'Curate',
        path: 'curate_image',
        enabled: projectIsConverting(projectStatus),
        hidden: !projectIsConverting(projectStatus),
      },
      {
        name: 'Validate',
        path: 'validate',
        enabled: projectIsConverting(projectStatus),
      },
      {
        name: 'Export',
        path: 'export',
        enabled: projectIsCompleted(projectStatus),
      },
    ],
  }

  const sections = [projectSection, metadataSection, imageSection, finalizeSection]
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
      element={project.uid !== '' && <Curate project={project} showImages={false} />}
    />,
    <Route
      key="download"
      path="/download"
      element={
        project.uid !== '' && (
          <DownloadImages
            project={project}
            nextView="curate_image"
            changeView={changeView}
          />
        )
      }
    />,
    <Route
      key="curateImage"
      path="/curate_image"
      element={project.uid !== '' && <Curate project={project} showImages={true} />}
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
