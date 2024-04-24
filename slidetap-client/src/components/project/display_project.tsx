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

import Batches from 'components/project/batches'
import Curate from 'components/project/curate'
import Overview from 'components/project/overview'
import PreProcessImages from 'components/project/pre_process_images'
import ProcessImages from 'components/project/process_images'
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

function projectIsPreProcessing(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.METADATA_SEARCH_COMPLETE ||
    projectStatus === ProjectStatus.IMAGE_PRE_PROCESSING ||
    projectStatus === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
  )
}

function projectIsImageEditable(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.IMAGE_PRE_PROCESSING ||
    projectStatus === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE
  )
}

function projectIsProcessing(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.IMAGE_PRE_PROCESSING_COMPLETE ||
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
          if (status !== project.status) {
            const updatedProject = project
            updatedProject.status = status
            setProject(project)
          }
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
        path: 'pre_process_images',
        enabled: projectIsPreProcessing(project.status),
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
        path: 'process_images',
        enabled: projectIsProcessing(project.status),
      },
      {
        name: 'Curate',
        path: 'curate_image',
        enabled: projectIsProcessing(project.status),
      },
      {
        name: 'Validate',
        path: 'validate',
        enabled: projectIsProcessing(project.status),
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
      key="curate_metadata"
      path="/curate_metadata"
      element={project.uid !== '' && <Curate project={project} showImages={false} />}
    />,
    <Route
      key="pre_process_images"
      path="/pre_process_images"
      element={
        project.uid !== '' && (
          <PreProcessImages project={project} setProject={setProject} />
        )
      }
    />,
    <Route
      key="curate_image"
      path="/curate_image"
      element={project.uid !== '' && <Curate project={project} showImages={true} />}
    />,
    <Route
      key="process_images"
      path="/process_images"
      element={
        project.uid !== '' && (
          <ProcessImages project={project} setProject={setProject} />
        )
      }
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
