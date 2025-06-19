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

import {
  AssignmentTurnedIn,
  Dataset,
  Download,
  DownloadDone,
  Downloading,
  Grading,
  HourglassBottom,
  HourglassEmpty,
  HourglassFull,
  MoveToInbox,
  RateReview,
} from '@mui/icons-material'
import SearchIcon from '@mui/icons-material/Search'
import SettingsIcon from '@mui/icons-material/Settings'
import StorageIcon from '@mui/icons-material/Storage'
import { LinearProgress } from '@mui/material'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import React, { useState } from 'react'
import { Route, useNavigate } from 'react-router-dom'
import ListBatches from 'src/components/project/batch/list_batches'
import PreProcessImages from 'src/components/project/batch/pre_process_images'
import ProcessImages from 'src/components/project/batch/process_images'
import Curate from 'src/components/project/curate'
import ProjectSettings from 'src/components/project/project_settings'
import Export from 'src/components/project/submit'
import Validate from 'src/components/project/validate/validate'
import SideBar, { type MenuSection } from 'src/components/side_bar'
import { BatchStatus, BatchStatusStrings } from 'src/models/batch_status'
import { ProjectStatus, ProjectStatusStrings } from 'src/models/project_status'
import batchApi from 'src/services/api/batch.api'
import datasetApi from 'src/services/api/dataset_api'
import projectApi from 'src/services/api/project_api'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import CompleteBatches from './batch/complete_batch'
import Search from './batch/search'
import DatasetSettings from './dataset_settings'

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

interface DisplayProjectProps {
  projectUid: string
}

export default function DisplayProject({
  projectUid,
}: DisplayProjectProps): React.ReactElement {
  const [view, setView] = useState<string>('')
  const [batchUid, setBatchUid] = useState<string>()
  const navigate = useNavigate()
  const rootSchema = useSchemaContext()
  const projectQuery = useQuery({
    queryKey: ['project', projectUid],
    queryFn: async () => {
      return await projectApi.get(projectUid)
    },
    refetchInterval: 5000,
    placeholderData: keepPreviousData,
  })
  const datasetQuery = useQuery({
    queryKey: ['dataset', projectQuery.data?.datasetUid],
    queryFn: async () => {
      if (!projectQuery.data?.uid) {
        return undefined
      }
      return await datasetApi.get(projectQuery.data.datasetUid)
    },
    enabled: !!projectQuery.data?.datasetUid,
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
    datasetQuery.data === undefined ||
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
    title: 'Project',
    name: projectQuery.data.name,
    description: ProjectStatusStrings[projectQuery.data.status],
    items: [
      {
        name: 'Settings',
        path: 'settings',
        icon: <SettingsIcon />,
        description: 'Project settings',
      },
      {
        name: 'Dataset',
        path: 'dataset',
        icon: <Dataset />,
        description: 'Dataset settings',
      },
      {
        name: 'Batches',
        path: 'batches',
        icon: <StorageIcon />,
        description: 'Batches in project',
      },
      {
        name: 'Curate',
        path: 'curate_dataset',
        icon: <RateReview />,
        description: 'Curate items in project',
      },
      {
        name: 'Export',
        path: 'export',
        enabled: projectIsCompleted(projectQuery.data.status),
        icon: <MoveToInbox />,
        description: 'Export project data',
      },
    ],
  }

  const batchection: MenuSection = {
    title: 'Batch',
    name: batchQuery.data.name,
    description: BatchStatusStrings[batchQuery.data.status],
    items: [
      {
        name: 'Search',
        path: 'search',
        enabled: batchIsSearchable(batchQuery.data.status),
        icon: <SearchIcon />,
        description: 'Search for items',
      },
      {
        name: 'Curate',
        path: 'curate_batch',
        enabled:
          batchIsImageEditable(batchQuery.data.status) ||
          batchIsProcessing(batchQuery.data.status) ||
          batchIsMetadataEditable(batchQuery.data.status),
        icon: <RateReview />,
        description: 'Curate items in batch',
      },
      {
        name: 'Pre-process',
        path: 'pre_process_images',
        enabled: batchIsPreProcessing(batchQuery.data.status),
        icon:
          batchQuery.data.status === BatchStatus.IMAGE_PRE_PROCESSING ? (
            <Downloading />
          ) : batchQuery.data.status === BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE ? (
            <DownloadDone />
          ) : (
            <Download />
          ),
        description: 'Pre-process images in batch',
      },
      {
        name: 'Post-process',
        path: 'process_images',
        enabled: batchIsProcessing(batchQuery.data.status),
        icon:
          batchQuery.data.status === BatchStatus.IMAGE_POST_PROCESSING ? (
            <HourglassBottom />
          ) : batchQuery.data.status === BatchStatus.IMAGE_POST_PROCESSING_COMPLETE ? (
            <HourglassFull />
          ) : (
            <HourglassEmpty />
          ),
        description: 'Post-process images in batch',
      },

      {
        name: 'Validate',
        path: 'validate',
        enabled: batchIsProcessing(batchQuery.data.status),
        icon: <Grading />,
        description: 'Validate items in batch',
      },
      {
        name: 'Complete',
        path: 'complete',
        enabled: batchIsProcessed(batchQuery.data.status),
        icon: <AssignmentTurnedIn />,
        description: 'Complete batch',
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
      key="dataset_settings"
      path="/dataset"
      element={<DatasetSettings dataset={datasetQuery.data} />}
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
        />
      }
    />,
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
          batch={batchQuery.data}
          itemSchemas={[
            ...Object.values(rootSchema.samples),
            ...Object.values(rootSchema.images),
            ...Object.values(rootSchema.observations),
            ...Object.values(rootSchema.annotations),
          ]}
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
