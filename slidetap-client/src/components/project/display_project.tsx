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

import { LinearProgress } from '@mui/material'
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
import { type Project } from 'models/project'
import { ProjectStatus, ProjectStatusStrings } from 'models/status'
import React, { useState } from 'react'
import { useQuery, useQueryClient } from 'react-query'
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
  const [view, setView] = useState<string>('')
  const navigate = useNavigate()
  const projectUid = window.location.pathname.split('project/').pop()?.split('/')[0]
  const queryClient = useQueryClient()
  const projectQuery = useQuery({
    queryKey: ['project', projectUid],
    queryFn: async () => {
      if (projectUid === undefined) {
        return undefined
      }
      return await projectApi.get(projectUid)
    },
    enabled: projectUid !== undefined,
    refetchInterval: 5000,
  })
  const mutateProject = (project: Project): void => {
    queryClient.setQueryData(['project', project.uid], project)
  }
  if (projectQuery.data === undefined) {
    return <LinearProgress />
  }
  function changeView(view: string): void {
    setView(view)
    navigate(view)
  }
  const projectSection: MenuSection = {
    name: 'Project: ' + projectQuery.data.name,
    description: ProjectStatusStrings[projectQuery.data.status],
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
        enabled: projectIsSearchable(projectQuery.data.status),
      },
      {
        name: 'Curate',
        path: 'curate_metadata',
        enabled: projectIsMetadataEditable(projectQuery.data.status),
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
        enabled: projectIsPreProcessing(projectQuery.data.status),
      },
      {
        name: 'Curate',
        path: 'curate_image',
        enabled: projectIsImageEditable(projectQuery.data.status),
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
        enabled: projectIsProcessing(projectQuery.data.status),
      },
      {
        name: 'Curate',
        path: 'curate_image',
        enabled: projectIsProcessing(projectQuery.data.status),
      },
      {
        name: 'Validate',
        path: 'validate',
        enabled: projectIsProcessing(projectQuery.data.status),
      },
      {
        name: 'Export',
        path: 'export',
        enabled: projectIsCompleted(projectQuery.data.status),
      },
    ],
  }

  const sections = [projectSection, metadataSection, imageSection, finalizeSection]
  const routes = [
    <Route
      key="overview"
      path="/"
      element={<Overview project={projectQuery.data} />}
    />,
    <Route
      key="settings"
      path="/settings"
      element={<Settings project={projectQuery.data} setProject={mutateProject} />}
    />,
    <Route
      key="batches"
      path="/batches"
      element={<Batches project={projectQuery.data} />}
    />,
    <Route
      key="search"
      path="/search"
      element={
        <Search
          project={projectQuery.data}
          setProject={mutateProject}
          nextView="curate_metadata"
          changeView={changeView}
        />
      }
    />,
    <Route
      key="curate_metadata"
      path="/curate_metadata"
      element={
        projectQuery.data.uid !== '' && (
          <Curate project={projectQuery.data} showImages={false} />
        )
      }
    />,
    <Route
      key="pre_process_images"
      path="/pre_process_images"
      element={
        projectQuery.data.uid !== '' && (
          <PreProcessImages project={projectQuery.data} setProject={mutateProject} />
        )
      }
    />,
    <Route
      key="curate_image"
      path="/curate_image"
      element={
        projectQuery.data.uid !== '' && (
          <Curate project={projectQuery.data} showImages={true} />
        )
      }
    />,
    <Route
      key="process_images"
      path="/process_images"
      element={
        projectQuery.data.uid !== '' && (
          <ProcessImages project={projectQuery.data} setProject={mutateProject} />
        )
      }
    />,
    <Route
      key="validate"
      path="/validate"
      element={projectQuery.data.uid !== '' && <Validate project={projectQuery.data} />}
    />,
    <Route
      key="export"
      path="/export"
      element={
        projectQuery.data.uid !== '' && (
          <Export setProject={mutateProject} project={projectQuery.data} />
        )
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
