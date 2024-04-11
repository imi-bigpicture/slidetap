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

import type { Project, ProjectValidation } from 'models/project'
import type { ProjectStatus } from 'models/status'

import { get, post, postFile } from 'services/api/api_methods'

const projectApi = {
  create: async (name: string) => {
    return await post('project/create', { name }).then<Project>(
      async (response) => await response.json(),
    )
  },

  update: async (project: Project) => {
    return await post(`project/${project.uid}/update`, project).then<Project>(
      async (response) => await response.json())
  },

  get: async (projectUid: string) => {
    return await get(`project/${projectUid}`).then<Project>(
      async (response) => await response.json(),
    )
  },

  getStatus: async (projectUid: string) => {
    return await get(`project/${projectUid}/status`).then<ProjectStatus>(
      async (response) => await response.json(),
    )
  },

  getView: async (projectUid: string, view: string) => {
    return await get(`project/${projectUid}/select/${view}`).then<Project>(
      async (response) => await response.json(),
    )
  },

  getProjects: async () => {
    return await get('project').then<Project[]>(
      async (response) => await response.json(),
    )
  },

  delete: async (projectUid: string) => {
    return await post(`project/${projectUid}/delete`)
  },

  uploadProjectFile: async (projectUid: string, file: File) => {
    return await postFile(`project/${projectUid}/uploadFile`, file).then<Project>(
      async (response) => await response.json())
  },

  getCount: async (projectUid: string, itemSchemaUid: string, selected?: boolean) => {
    const path = `project/${projectUid}/items/${itemSchemaUid}/count`
    const args = new Map<string, string>()
    if (selected !== undefined) {
      args.set('selected', selected.toString())
    }
    return await get(path, args).then<number>(async (response) => await response.json())
  },

  preprocess: async (projectUid: string) => {
    return await post(`project/${projectUid}/preprocess`).then<Project>(
      async (response) => await response.json())
  },

  process: async (projectUid: string) => {
    return await post(`project/${projectUid}/process`).then<Project>(
      async (response) => await response.json())
  },

  export: async (projectUid: string) => {
    return await post(`project/${projectUid}/export`).then<Project>(
      async (response) => await response.json())
  },
  getValidation: async (projectUid: string) => {
    return await get(`project/${projectUid}/validation`).then<ProjectValidation>(
      async (response) => await response.json(),
    )
  }
}

export default projectApi
