import Batches from 'components/project/batches'
import Curate from 'components/project/curate'
import Overview from 'components/project/overview'
import PreProcessImages from 'components/project/preprocess'
import Process from 'components/project/process'
import Progress from 'components/project/progress'
import Search from 'components/project/search'
import Settings from 'components/project/settings'
import Export from 'components/project/submit'
import Validate from 'components/project/validate/validate'
import SideBar, { type MenuSection } from 'components/side_bar'
import Spinner from 'components/spinner'
import type { Project } from 'models/project'
import { ProjectStatus, ProjectStatusStrings } from 'models/status'
import React, { useEffect, useState } from 'react'
import { Route, useNavigate } from 'react-router-dom'
import projectApi from 'services/api/project_api'

function projectIsSearchable(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.INITIALIZED ||
    projectIsMetadataEditable(projectStatus)
  )
}

function projectIsMetadataEditable(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.METADATA_SEARCHING ||
    projectStatus === ProjectStatus.METADATA_SEARCH_COMPLETE
  )
}

function projectIsDownloadable(projectStatus?: ProjectStatus): boolean {
  return projectStatus === ProjectStatus.METADATA_SEARCH_COMPLETE
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
  const [project, setProject] = useState<Project>()
  const [view, setView] = useState<string>('')
  const navigate = useNavigate()
  const projectUid = window.location.pathname.split('project/').pop()?.split('/')[0]

  useEffect(() => {
    const getProject = (): void => {
      if (projectUid !== undefined) {
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
          const updatedProject = project
          updatedProject.status = status
          setProject(project)
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
  if (project === undefined) {
    return <Spinner loading={project === undefined}>loading</Spinner>
  }
  function changeView(view: string): void {
    setView(view)
    navigate(view)
  }
  const projectSection: MenuSection = {
    name: 'Project: ' + project?.name,
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
        enabled: projectIsSearchable(project.status),
      },
      {
        name: 'Curate',
        path: 'curate_metadata',
        enabled: projectIsMetadataEditable(project.status),
        // hidden: !projectIsMetadataEditable(project.status),
      },
    ],
  }
  const imageSection = {
    name: 'Image',
    items: [
      {
        name: 'Pre-process',
        path: 'download',
        enabled: projectIsDownloadable(project.status),
      },
      {
        name: 'Curate',
        path: 'curate_image',
        enabled: projectIsImageEditable(project.status),
        // hidden: !projectIsImageEditable(project.status),
      },
    ],
  }
  const finalizeSection = {
    name: 'Finalize',
    items: [
      {
        name: 'Process',
        path: 'process',
        enabled: projectIsProcessable(project.status),
        hidden: projectIsConverting(project.status),
      },
      {
        name: 'Process',
        path: 'progress',
        enabled: projectIsConverting(project.status),
        hidden: !projectIsConverting(project.status),
      },
      {
        name: 'Curate',
        path: 'curate_image',
        enabled: projectIsConverting(project.status),
        // hidden: !projectIsConverting(project.status),
      },
      {
        name: 'Validate',
        path: 'validate',
        enabled: projectIsConverting(project.status),
      },
      {
        name: 'Export',
        path: 'export',
        enabled: projectIsCompleted(project.status),
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
        <Search
          project={project}
          setProject={setProject}
          nextView="curate_metadata"
          changeView={changeView}
        />
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
          <PreProcessImages
            project={project}
            setProject={setProject}
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
          <Process
            project={project}
            setProject={setProject}
            nextView="progress"
            changeView={changeView}
          />
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
      element={
        project.uid !== '' && <Export setProject={setProject} project={project} />
      }
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
