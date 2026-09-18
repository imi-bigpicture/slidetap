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
  AccountTree,
  AssignmentTurnedIn,
  Dataset as DatasetIcon,
  Download,
  DownloadDone,
  Downloading,
  Flag,
  Grading,
  HourglassBottom,
  HourglassEmpty,
  HourglassFull,
  MoveToInbox,
  Notes,
  PhotoLibrary,
  QuestionMark,
  RateReview,
  TableChart,
} from '@mui/icons-material'
import SearchIcon from '@mui/icons-material/Search'
import SettingsIcon from '@mui/icons-material/Settings'
import StorageIcon from '@mui/icons-material/Storage'
import { LinearProgress } from '@mui/material'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import React, { useEffect, useRef, useState } from 'react'
import { Route, useLocation, useSearchParams } from 'react-router-dom'
import ListBatches from 'src/components/project/batch/list_batches'
import PreProcessImages from 'src/components/project/batch/pre_process_images'
import ProcessImages from 'src/components/project/batch/process_images'
import Curate from 'src/components/project/curate'
import Unmapped from 'src/components/project/unmapped'
import Review from 'src/components/project/review'
import HierarchyPage from 'src/pages/hierarchy'
import ImagesForItemPage from 'src/pages/images_for_item'
import ItemPage from 'src/pages/item'
import OverviewPage from 'src/pages/overview'
import ProjectSettings from 'src/components/project/project_settings'
import Export from 'src/components/project/submit'
import Validate from 'src/components/project/validate/validate'
import SideBar, { type MenuSection } from 'src/components/side_bar'
import { assertExtensionPath, useExtensions } from 'src/extensions'
import { Batch } from 'src/models/batch'
import { BatchStatus, BatchStatusStrings } from 'src/models/batch_status'
import { Dataset } from 'src/models/dataset'
import { Project } from 'src/models/project'
import { ProjectStatus, ProjectStatusStrings } from 'src/models/project_status'
import batchApi from 'src/services/api/batch.api'
import datasetApi from 'src/services/api/dataset_api'
import itemApi from 'src/services/api/item_api'
import projectApi from 'src/services/api/project_api'
import { queryKeys } from 'src/services/query_keys'
import { useSchemaContext } from '../../contexts/schema/schema_context'
import CompleteBatches from './batch/complete_batch'
import Search from './batch/search'
import DatasetSettings from './dataset_settings'
import {
  readAddressedBatch,
  readRememberedBatch,
  rememberBatch,
  withSelectedBatch,
} from './selected_batch'

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

/** `batchIsProcessing`, plus a completed batch: for the views of the images
 * themselves, which stay meaningful to look at once the batch is done. Not
 * folded into `batchIsProcessing` itself, whose other callers (Curate,
 * Review) are for changing the batch rather than looking at its images, and
 * stay closed once it is completed. */
function batchIsProcessingOrCompleted(batchStatus?: BatchStatus): boolean {
  return batchIsProcessing(batchStatus) || batchStatus === BatchStatus.COMPLETED
}

function batchIsProcessed(batchStatus?: BatchStatus): boolean {
  return (
    batchStatus === BatchStatus.IMAGE_POST_PROCESSING_COMPLETE ||
    batchStatus === BatchStatus.IMAGE_STORING
  )
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

/**
 * Point each entry at the view as it was last left, so that stepping into an
 * item and back lands where the work was rather than at the top of a fresh
 * table.
 *
 * What is remembered is the address, so only what the view puts there comes
 * back — which tab, which filters. `visited` is carried between renders by the
 * caller and written here as the current view is passed through.
 *
 * The batch the bar is on is written into the entries whose view is that
 * batch's, over whatever a remembered address said, so that an entry left
 * before the bar was moved does not take it back. It is taken off the rest:
 * nothing about the project's own views is a batch's, so naming one there says
 * something that is not true.
 */
function rememberVisited(
  sections: MenuSection[],
  current: string,
  visited: Record<string, string>,
  selectedBatchUid: string | undefined,
  batchViewPaths: ReadonlySet<string>,
): MenuSection[] {
  const path = current.split('?')[0]
  const entry = sections
    .flatMap((section) => section.items)
    .find((item) => item.path === path)
  if (entry !== undefined) {
    visited[entry.path] = current
  }
  return sections.map((section) => ({
    ...section,
    items: section.items.map((item) => ({
      ...item,
      to: withSelectedBatch(
        visited[item.path] ?? item.to ?? item.path,
        batchViewPaths.has(item.path) ? selectedBatchUid : undefined,
      ),
    })),
  }))
}

export default function DisplayProject({
  projectUid,
}: DisplayProjectProps): React.ReactElement {
  const [project, setProject] = useState<Project>()
  const [dataset, setDataset] = useState<Dataset>()
  const [batch, setBatch] = useState<Batch>()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  // Which batch the bar is on. What the address names, where it is a view of
  // one and so names it; otherwise the last it was on, which is what the
  // project's own views leave the bar showing.
  const addressedBatchUid = readAddressedBatch(searchParams)
  const [lastBatchUid, setLastBatchUid] = useState<string | undefined>(() =>
    readRememberedBatch(projectUid),
  )
  // Where each entry of the bar was last left, so it can be gone back to.
  const visitedRef = useRef<Record<string, string>>({})
  // Which view is open is what the address says, not something held beside it:
  // the bar is links now, and so is everything else that opens a view.
  const basePath = `/project/${projectUid}`
  const view = location.pathname.startsWith(`${basePath}/`)
    ? location.pathname.slice(basePath.length + 1)
    : ''
  // The item an item-level view is of, for the section that names it.
  const itemUid = /^(?:item|images_for_item)\/([^/]+)/.exec(view)?.[1]
  // An item view is the same route whether the item was opened from a batch or
  // from the whole project, so how far its stepping reaches is what the address
  // says. Carried from one view of the item to the next.
  const openedBatchUid = new URLSearchParams(location.search).get('batchUid')
  const itemScope = openedBatchUid !== null ? `?batchUid=${openedBatchUid}` : ''
  const itemQuery = useQuery({
    queryKey: queryKeys.item.detail(itemUid ?? ''),
    queryFn: async () => await itemApi.get(itemUid ?? ''),
    enabled: itemUid !== undefined,
    // Stepping to the next item would otherwise empty the section until the
    // item arrives, so the bar drops the whole thing and puts it back.
    placeholderData: keepPreviousData,
  })
  const itemIdentifier = itemQuery.data?.identifier
  const rootSchema = useSchemaContext()
  const extensions = useExtensions()
  const itemSchema =
    itemQuery.data === undefined
      ? undefined
      : {
          ...rootSchema.samples,
          ...rootSchema.images,
          ...rootSchema.observations,
          ...rootSchema.annotations,
        }[itemQuery.data.schemaUid]
  const projectQuery = useQuery({
    queryKey: queryKeys.project.detail(projectUid),
    queryFn: async () => {
      return await projectApi.get(projectUid)
    },
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === ProjectStatus.IN_PROGRESS || status === ProjectStatus.EXPORTING
        ? 5000
        : false
    },
    placeholderData: keepPreviousData,
  })
  const datasetQuery = useQuery({
    queryKey: queryKeys.dataset.detail(projectQuery.data?.datasetUid || ''),
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
    queryKey: queryKeys.batch.list(projectUid),
    queryFn: async () => await batchApi.getBatches(projectUid),
  })
  const batches = batchesQuery.data
  // The first batch where nothing names one, and where what is named is not
  // one the project holds — an address kept from another project, or a batch
  // deleted since.
  const namedBatchUid = addressedBatchUid ?? lastBatchUid
  const batchUid =
    batches === undefined
      ? namedBatchUid
      : batches.some((each) => each.uid === namedBatchUid)
        ? namedBatchUid
        : batches[0]?.uid
  // Held, and kept for the tab, so that the project's own views leave the bar
  // on the batch that was being worked rather than sending it back to the
  // first — whether they are walked to or reloaded.
  useEffect(() => {
    if (batchUid === undefined || batchUid === lastBatchUid) {
      return
    }
    setLastBatchUid(batchUid)
    rememberBatch(projectUid, batchUid)
  }, [batchUid, lastBatchUid, projectUid])
  const batchQuery = useQuery({
    queryKey: queryKeys.batch.detail(batchUid || ''),
    queryFn: async () => {
      if (batchUid === undefined) {
        return undefined
      }
      return await batchApi.get(batchUid)
    },
    // Only once the batches are known to hold it: an address kept from another
    // project names a batch this one does not have, and asking for it answers
    // with a fault rather than with the batch the bar falls back to.
    enabled: batchUid !== undefined && batches !== undefined,
    refetchInterval: (query) => {
      const status = query.state.data?.status
      const activeStatuses = [
        BatchStatus.METADATA_SEARCHING,
        BatchStatus.IMAGE_PRE_PROCESSING,
        BatchStatus.IMAGE_POST_PROCESSING,
        BatchStatus.IMAGE_STORING,
      ]
      return status !== undefined && activeStatuses.includes(status) ? 2000 : false
    },
    placeholderData: keepPreviousData,
  })
  useEffect(() => {
    if (projectQuery.data !== undefined) {
      setProject((current) => {
        if (current === undefined) {
          return projectQuery.data
        }
        // Update server-driven fields (e.g. status) without overwriting local edits
        return { ...current, status: projectQuery.data.status }
      })
    }
  }, [projectQuery.data])
  useEffect(() => {
    if (datasetQuery.data !== undefined) {
      setDataset(datasetQuery.data)
    }
  }, [datasetQuery.data])
  useEffect(() => {
    if (batchQuery.data !== undefined) {
      setBatch(batchQuery.data)
    }
  }, [batchQuery.data])
  if (project === undefined || dataset === undefined || batch === undefined) {
    return <LinearProgress />
  }
  const projectSection: MenuSection = {
    title: 'Project',
    name: project.name,
    description: ProjectStatusStrings[project.status],
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
        icon: <DatasetIcon />,
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
        name: 'Review',
        path: 'review_dataset',
        icon: <Flag />,
        description: 'Review items in project flagged for review',
      },
      {
        name: 'Unmapped',
        path: 'unmapped_dataset',
        icon: <QuestionMark />,
        description: 'Values in the project with no mapping',
      },
      {
        name: 'Export',
        path: 'export',
        enabled: projectIsCompleted(project.status),
        icon: <MoveToInbox />,
        description: 'Export project data',
      },
    ],
  }

  const batchSection: MenuSection = {
    title: 'Batch',
    name: batch.name,
    description: batch.statusMessage
      ? `${BatchStatusStrings[batch.status]}: ${batch.statusMessage}`
      : BatchStatusStrings[batch.status],
    items: [
      {
        name: 'Search',
        path: 'search',
        enabled: batchIsSearchable(batch.status),
        icon: <SearchIcon />,
        description: 'Search for items',
      },
      {
        name: 'Curate',
        path: 'curate_batch',
        enabled:
          batchIsImageEditable(batch.status) ||
          batchIsProcessing(batch.status) ||
          batchIsMetadataEditable(batch.status),
        icon: <RateReview />,
        description: 'Curate items in batch',
      },
      {
        name: 'Review',
        path: 'review_batch',
        enabled:
          batchIsImageEditable(batch.status) ||
          batchIsProcessing(batch.status) ||
          batchIsMetadataEditable(batch.status),
        icon: <Flag />,
        description: 'Review items in batch flagged for review',
      },
      {
        name: 'Unmapped',
        path: 'unmapped_batch',
        icon: <QuestionMark />,
        description: 'Values in the batch with no mapping',
      },
      {
        name: 'Pre-process',
        path: 'pre_process_images',
        enabled: batchIsPreProcessing(batch.status),
        icon:
          batch.status === BatchStatus.IMAGE_PRE_PROCESSING ? (
            <Downloading />
          ) : batch.status === BatchStatus.IMAGE_PRE_PROCESSING_COMPLETE ? (
            <DownloadDone />
          ) : (
            <Download />
          ),
        description: 'Pre-process images in batch',
      },
      {
        name: 'Post-process',
        path: 'process_images',
        enabled: batchIsProcessingOrCompleted(batch.status),
        icon:
          batch.status === BatchStatus.IMAGE_POST_PROCESSING ? (
            <HourglassBottom />
          ) : batch.status === BatchStatus.IMAGE_POST_PROCESSING_COMPLETE ? (
            <HourglassFull />
          ) : (
            <HourglassEmpty />
          ),
        description: 'Post-process images in batch',
      },

      {
        name: 'Validate',
        path: 'validate',
        enabled: batchIsProcessingOrCompleted(batch.status),
        icon: <Grading />,
        description: 'Validate items in batch',
      },
      {
        name: 'Complete',
        path: 'complete',
        enabled: batchIsProcessed(batch.status),
        icon: <AssignmentTurnedIn />,
        description: 'Complete batch',
      },
    ],
  }
  const reservedPaths: ReadonlySet<string> = new Set([
    ...projectSection.items.map((item) => item.path),
    ...batchSection.items.map((item) => item.path),
  ])
  const seenExtensionPaths = new Set<string>()
  const extensionSections: MenuSection[] = (extensions.projectSections ?? []).map(
    (section) => ({
      title: section.title,
      name: '',
      items: section.pages.map((page) => {
        assertExtensionPath(page.path, reservedPaths, seenExtensionPaths)
        return {
          name: page.label,
          path: page.path,
          icon: page.icon,
          enabled:
            typeof page.enabled === 'function'
              ? page.enabled(project, batch)
              : page.enabled,
          description: page.description,
        }
      }),
    }),
  )
  const extensionRoutes = (extensions.projectSections ?? []).flatMap((section) =>
    section.pages.map((page) => (
      <Route key={page.path} path={`/${page.path}`} element={page.element} />
    )),
  )
  // Only while one is open: an item is not a stage of the project the way the
  // sections above are, it is what a stage was opened on, so it comes and goes
  // with the view rather than sitting there empty.
  const itemSection: MenuSection | undefined =
    itemUid === undefined || itemSchema === undefined
      ? undefined
      : {
          title: 'Item',
          name: itemIdentifier ?? '',
          description: itemSchema.displayName,
          items: [
            {
              name: 'Details',
              path: `item/${itemUid}`,
              to: `item/${itemUid}${itemScope}`,
              icon: <Notes />,
            },
            ...rootSchema.overviewLayouts
              .filter((layout) => layout.schemaUid === itemSchema.uid)
              .map((layout) => ({
                name: layout.displayName,
                path: `item/${itemUid}/overview/${layout.uid}`,
                to: `item/${itemUid}/overview/${layout.uid}${itemScope}`,
                icon: <TableChart />,
              })),
            ...rootSchema.hierarchyLayouts
              .filter((layout) => layout.schemaUid === itemSchema.uid)
              .map((layout) => ({
                name: layout.displayName,
                path: `item/${itemUid}/hierarchy/${layout.uid}`,
                to: `item/${itemUid}/hierarchy/${layout.uid}${itemScope}`,
                icon: <AccountTree />,
              })),
            {
              name: 'Images',
              path: `images_for_item/${itemUid}`,
              to: `images_for_item/${itemUid}${itemScope}`,
              icon: <PhotoLibrary />,
            },
          ],
        }
  const sections = rememberVisited(
    [
      projectSection,
      batchSection,
      ...extensionSections,
      ...(itemSection !== undefined ? [itemSection] : []),
    ],
    view + location.search,
    visitedRef.current,
    batchUid,
    // The batch section's own views, which are the batch's and say so.
    new Set(batchSection.items.map((item) => item.path)),
  )
  const routes = [
    // The views of one item, routed here so that the project's bar stays
    // beside them.
    <Route key="item" path="/item/:itemUid" element={<ItemPage />} />,
    <Route
      key="item_overview"
      path="/item/:itemUid/overview/:overviewLayoutUid"
      element={<OverviewPage />}
    />,
    <Route
      key="item_hierarchy"
      path="/item/:itemUid/hierarchy/:hierarchyLayoutUid"
      element={<HierarchyPage />}
    />,
    <Route
      key="item_images"
      path="/images_for_item/:itemUid"
      element={<ImagesForItemPage />}
    />,
    <Route
      key="project_settings"
      path="/settings"
      element={<ProjectSettings project={project} setProject={setProject} />}
    />,
    <Route
      key="dataset_settings"
      path="/dataset"
      element={<DatasetSettings dataset={dataset} setDataset={setDataset} />}
    />,
    <Route
      key="batches"
      path="/batches"
      element={<ListBatches project={project} setBatchUid={setLastBatchUid} />}
    />,
    <Route
      key="unmapped_dataset"
      path="/unmapped_dataset"
      element={<Unmapped project={project} />}
    />,
    <Route
      key="unmapped_batch"
      path="/unmapped_batch"
      element={<Unmapped project={project} batch={batch} />}
    />,
    <Route
      key="curate_dataset"
      path="/curate_dataset"
      element={
        <Curate
          project={project}
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
      key="review_dataset"
      path="/review_dataset"
      element={<Review project={project} />}
    />,
    <Route
      key="review_batch"
      path="/review_batch"
      element={<Review project={project} batch={batch} />}
    />,
    <Route key="search" path="/search" element={<Search batch={batch} />} />,
    <Route
      key="curate_batch"
      path="/curate_batch"
      element={
        <Curate
          project={project}
          batch={batch}
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
      element={<PreProcessImages project={project} batch={batch} />}
    />,

    <Route
      key="process_images"
      path="/process_images"
      element={<ProcessImages project={project} batch={batch} />}
    />,
    <Route
      key="validate"
      path="/validate"
      element={<Validate project={project} batch={batch} />}
    />,
    <Route
      key="complete"
      path="/complete"
      element={<CompleteBatches batch={batch} />}
    />,
    <Route key="export" path="/export" element={<Export project={project} />} />,
    ...extensionRoutes,
  ]
  return (
    <SideBar
      sections={sections}
      routes={routes}
      selectedView={view}
      basePath={basePath}
    />
  )
}
