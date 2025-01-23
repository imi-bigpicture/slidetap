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

import type { Project } from 'src/models/project'
import type { ProjectStatus } from 'src/models/project_status'
import type { ProjectValidation } from 'src/models/validation'

import { del, get, post } from 'src/services/api/api_methods'

const projectApi = {
  create: async (name: string) => {
    return await post('project/create', { name }).then<Project>(
      async (response) => await response.json(),
    )
  },

  update: async (project: Project) => {
    return await post(`project/${project.uid}`, project).then<Project>(
      async (response) => await response.json())
  },

  get: async (projectUid: string) => {
    return await get(`project/${projectUid}`).then<Project>(
      async (response) => await response.json(),
    )
  },

  getProjects: async (status?: ProjectStatus) => {
    const params = new URLSearchParams();
    if (status !== undefined) {
      params.append('status', status.toString())
    }
    const url = "project" + (params.size > 0 ? "?" + params.toString() : "")
    return await get(url).then<Project[]>(
      async (response) => await response.json(),
    )
  },

  delete: async (projectUid: string) => {
    return await del(`project/${projectUid}`)
  },

  export: async (projectUid: string) => {
    return await post(`project/${projectUid}/export`).then<Project>(
      async (response) => await response.json())
  },
  getValidation: async (projectUid: string) => {
    return await get(`project/${projectUid}/validation`).then<ProjectValidation>(
      async (response) => await response.json(),
    )
  },
  validateProject: async (projectUid: string) => {
    return await post(`project/${projectUid}/validate`)
  }
}

export default projectApi
