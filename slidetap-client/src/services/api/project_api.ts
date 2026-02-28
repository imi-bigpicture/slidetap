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

import { delete_, get, parseJsonResponse, post } from 'src/services/api/api_methods'

const projectApi = {
  create: async (name: string) => {
    const response = await post('projects/create', { name })
    return await parseJsonResponse<Project>(response)
  },

  update: async (project: Project) => {
    const response = await post(`projects/project/${project.uid}`, project)
    return await parseJsonResponse<Project>(response)
  },

  get: async (projectUid: string) => {
    const response = await get(`projects/project/${projectUid}`)
    return await parseJsonResponse<Project>(response)
  },

  getProjects: async (status?: ProjectStatus) => {
    const params = new URLSearchParams();
    if (status !== undefined) {
      params.append('status', status.toString())
    }
    const url = "projects" + (params.size > 0 ? "?" + params.toString() : "")
    const response = await get(url)
    return await parseJsonResponse<Project[]>(response)
  },

  delete: async (projectUid: string) => {
    return await delete_(`projects/project/${projectUid}`)
  },

  export: async (projectUid: string) => {
    const response = await post(`projects/project/${projectUid}/export`)
    return await parseJsonResponse<Project>(response)
  },
  getValidation: async (projectUid: string) => {
    const response = await get(`projects/project/${projectUid}/validation`)
    return await parseJsonResponse<ProjectValidation>(response)
  },
  validateProject: async (projectUid: string) => {
    return await post(`projects/project/${projectUid}/validate`)
  }
}

export default projectApi
