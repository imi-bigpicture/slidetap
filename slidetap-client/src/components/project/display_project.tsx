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
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import React, { useState } from 'react'
import { Route, useNavigate, useParams } from 'react-router-dom'
import ListBatches from 'src/components/project/batch/list_batches'
import PreProcessImages from 'src/components/project/batch/pre_process_images'
import ProcessImages from 'src/components/project/batch/process_images'
import Search from 'src/components/project/batch/search'
import Curate from 'src/components/project/curate'
import ProjectSettings from 'src/components/project/project_settings'
import Export from 'src/components/project/submit'
import Validate from 'src/components/project/validate/validate'
import SideBar, { type MenuSection } from 'src/components/side_bar'
import { BatchStatus, BatchStatusStrings } from 'src/models/batch_status'
import { ProjectStatus, ProjectStatusStrings } from 'src/models/project_status'
import batchApi from 'src/services/api/batch.api'
import projectApi from 'src/services/api/project_api'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import CompleteBatches from './batch/complete_batch'
import DisplayBatch from './batch/display_batch'

function batchIsSearchable(batchStatus?: BatchStatus): boolean {
  return batchStatus === BatchStatus.INITIALIZED || batchIsMetadataEditable(batchStatus)
}

function batchIsMetadataEditable(batchStatus?: BatchStatus): boolean {
  return (
    batchStatus === BatchStatus.METADATA_SEARCHING ||
    batchStatus === BatchStatus.METADATA_SEARCH_COMPLETE
  )
}

function batchIsPreProcessing(batchStatus?: BatchStatus): boolean {
  return (
    batchStatus === BatchStatus.METADATA_SEARCH_COMPLETE ||
    batchStatus === BatchStatus.IMAGE_PRE_PROCESSING ||
    batchStatus === BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
  )
}

function batchIsImageEditable(batchStatus?: BatchStatus): boolean {
  return (
    batchStatus === BatchStatus.IMAGE_PRE_PROCESSING ||
    batchStatus === BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE
  )
}

function batchIsProcessing(batchStatus?: BatchStatus): boolean {
  return (
    batchStatus === BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE ||
    batchStatus === BatchStatus.IMAGE_POST_PROCESSING ||
    batchStatus === BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
  )
}

function batchIsProcessed(batchStatus?: BatchStatus): boolean {
  return batchStatus === BatchStatus.IMAGE_POST_PROCESSING_COMPLETE
}

function projectIsCompleted(projectStatus?: ProjectStatus): boolean {
  return (
    projectStatus === ProjectStatus.COMPLETED ||
    projectStatus === ProjectStatus.EXPORTING ||
    projectStatus === ProjectStatus.EXPORT_COMPLETE
  )
}

export default function DisplayProject(): React.ReactElement {
  const [view, setView] = useState<string>('')
  const [batchUid, setBatchUid] = useState<string>()
  const navigate = useNavigate()
  const { projectUid } = useParams()
  const rootSchema = useSchemaContext()
  const projectQuery = useQuery({
    queryKey: ['project', projectUid],
    queryFn: async () => {
      if (projectUid === undefined) {
        return undefined
      }
      return await projectApi.get(projectUid)
    },
    enabled: projectUid != undefined,
    refetchInterval: 5000,
    placeholderData: keepPreviousData,
  })
  const batchesQuery = useQuery({
    queryKey: ['batches', projectUid],
    queryFn: async () => {
      if (projectUid === undefined) {
        return undefined
      }
      const batches = await batchApi.getBatches(projectUid)
      if (batchUid === undefined) {
        setBatchUid(batches[0].uid)
      }
      return batches
    },
    enabled: projectUid != undefined,
    refetchInterval: 5000,
    placeholderData: keepPreviousData,
  })
  const batchQuery = useQuery({
    queryKey: ['batch', batchUid],
    queryFn: async () => {
      if (batchUid === undefined) {
        return undefined
      }
      return await batchApi.get(batchUid)
    },
    enabled: batchUid != undefined,
    refetchInterval: 5000,
    placeholderData: keepPreviousData,
  })

  if (
    projectQuery.data === undefined ||
    batchesQuery.data === undefined ||
    batchQuery.data === undefined
  ) {
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
      { name: 'Settings', path: 'settings' },
      { name: 'Batches', path: 'batches' },
      { name: 'Curate', path: 'curate_dataset' },
      {
        name: 'Export',
        path: 'export',
        enabled: projectIsCompleted(projectQuery.data.status),
      },
    ],
  }

  const batchection: MenuSection = {
    name: 'Batch: ' + batchQuery.data.name,
    description: BatchStatusStrings[batchQuery.data.status],
    items: [
      { name: 'Settings', path: 'batch/' + batchQuery.data.uid },
      {
        name: 'Search',
        path: 'search',
        enabled: batchIsSearchable(batchQuery.data.status),
      },
      {
        name: 'Pre-process',
        path: 'pre_process_images',
        enabled: batchIsPreProcessing(batchQuery.data.status),
      },
      {
        name: 'Post-process',
        path: 'process_images',
        enabled: batchIsProcessing(batchQuery.data.status),
      },
      {
        name: 'Curate',
        path: 'curate_batch',
        enabled:
          batchIsImageEditable(batchQuery.data.status) ||
          batchIsProcessing(batchQuery.data.status) ||
          batchIsMetadataEditable(batchQuery.data.status),
      },
      {
        name: 'Validate',
        path: 'validate',
        enabled: batchIsProcessing(batchQuery.data.status),
      },
      {
        name: 'Complete',
        path: 'complete',
        enabled: batchIsProcessed(batchQuery.data.status),
      },
    ],
  }
  const sections = [projectSection, batchection]
  const routes = [
    <Route
      key="project_settings"
      path="/settings"
      element={<ProjectSettings project={projectQuery.data} />}
    />,
    <Route
      key="batches"
      path="/batches"
      element={<ListBatches project={projectQuery.data} setBatchUid={setBatchUid} />}
    />,
    <Route
      key="curate_dataset"
      path="/curate_dataset"
      element={
        <Curate
          project={projectQuery.data}
          itemSchemas={[
            ...Object.values(rootSchema.samples),
            ...Object.values(rootSchema.images),
            ...Object.values(rootSchema.observations),
            ...Object.values(rootSchema.annotations),
          ]}
          showImages={true}
        />
      }
    />,
    <Route path="/batch/:batchUid" element={<DisplayBatch />} />,
    <Route
      key="search"
      path="/search"
      element={
        <Search
          batch={batchQuery.data}
          nextView="curate_batch"
          changeView={changeView}
        />
      }
    />,
    <Route
      key="curate_batch"
      path="/curate_batch"
      element={
        <Curate
          project={projectQuery.data}
          batchUid={batchQuery.data.uid}
          itemSchemas={[
            ...Object.values(rootSchema.samples),
            ...Object.values(rootSchema.images),
            ...Object.values(rootSchema.observations),
            ...Object.values(rootSchema.annotations),
          ]}
          showImages={batchQuery.data.status > BatchStatus.METADATA_SEARCH_COMPLETE}
        />
      }
    />,
    <Route
      key="pre_process_images"
      path="/pre_process_images"
      element={<PreProcessImages project={projectQuery.data} batch={batchQuery.data} />}
    />,

    <Route
      key="process_images"
      path="/process_images"
      element={<ProcessImages project={projectQuery.data} batch={batchQuery.data} />}
    />,
    <Route
      key="validate"
      path="/validate"
      element={<Validate project={projectQuery.data} batch={batchQuery.data} />}
    />,
    <Route
      key="complete"
      path="/complete"
      element={<CompleteBatches batch={batchQuery.data} />}
    />,
    <Route
      key="export"
      path="/export"
      element={<Export project={projectQuery.data} />}
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
