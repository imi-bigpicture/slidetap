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

import type { PrivateAttributeSummary } from 'src/models/private_attribute_summary'
import type { Project } from 'src/models/project'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { AttributeMigrationIssue, ProjectMigration } from 'src/models/migration'
import type { ProjectActions } from 'src/models/project_actions'
import type { ProjectStatus } from 'src/models/project_status'
import type { ProjectValidation } from 'src/models/validation'

import {
  ApiError,
  delete_,
  get,
  parseJsonResponse,
  post,
  put,
} from 'src/services/api/api_methods'

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

  /** The migration of the project, null where it has none. */
  getMigration: async (projectUid: string) => {
    try {
      const response = await get(`projects/project/${projectUid}/migration`)
      return await parseJsonResponse<ProjectMigration>(response)
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        return null
      }
      throw error
    }
  },

  /** Create the migration of the project to another root schema, planned in
   * a task. */
  createMigration: async (projectUid: string) => {
    const response = await post(`projects/project/${projectUid}/migration`)
    return await parseJsonResponse<ProjectMigration>(response)
  },

  /** Resolve an attribute issue of the migration: a value, or null to leave it
   * empty or accept a dropped attribute. */
  resolveMigrationAttributeIssue: async (
    projectUid: string,
    attributeIssueUid: string,
    attribute: Attribute<AttributeValueTypes> | null,
  ) => {
    const response = await put(
      `projects/project/${projectUid}/migration/attribute-issues/${attributeIssueUid}`,
      attribute,
    )
    return await parseJsonResponse<AttributeMigrationIssue>(response)
  },

  /** Complete the migration, with every attribute issue resolved, in a task. */
  submitMigration: async (projectUid: string) => {
    const response = await post(`projects/project/${projectUid}/migration/submit`)
    return await parseJsonResponse<ProjectMigration>(response)
  },

  /** Revert the migration, setting the project back to the status it had. */
  revertMigration: async (projectUid: string) => {
    const response = await delete_(`projects/project/${projectUid}/migration`)
    return await parseJsonResponse<Project>(response)
  },

  getActions: async (projectUid: string) => {
    const response = await get(`projects/project/${projectUid}/actions`)
    return await parseJsonResponse<ProjectActions>(response)
  },

  getProjects: async (status?: ProjectStatus) => {
    const params = new URLSearchParams()
    if (status !== undefined) {
      params.append('status', status.toString())
    }
    const url = 'projects' + (params.size > 0 ? '?' + params.toString() : '')
    const response = await get(url)
    return await parseJsonResponse<Project[]>(response)
  },

  delete: async (projectUid: string) => {
    return await delete_(`projects/project/${projectUid}`)
  },

  /** Store the images of every locked batch of the project to the outbox. */
  storeImages: async (projectUid: string) => {
    const response = await post(`projects/project/${projectUid}/complete`)
    return await parseJsonResponse<Project>(response)
  },

  export: async (projectUid: string) => {
    const response = await post(`projects/project/${projectUid}/export`)
    return await parseJsonResponse<Project>(response)
  },
  repseudonymize: async (projectUid: string) => {
    const response = await post(`projects/project/${projectUid}/repseudonymize`)
    return await parseJsonResponse<{ changed: number }>(response)
  },
  clearPseudonyms: async (projectUid: string) => {
    const response = await post(`projects/project/${projectUid}/clear_pseudonyms`)
    return await parseJsonResponse<{ changed: number }>(response)
  },
  pseudonymizeIdentifiers: async (projectUid: string) => {
    const response = await post(
      `projects/project/${projectUid}/pseudonymize_identifiers`,
    )
    return await parseJsonResponse<{ changed: number }>(response)
  },
  getPrivateAttributes: async (projectUid: string) => {
    const response = await get(`projects/project/${projectUid}/private_attributes`)
    return await parseJsonResponse<PrivateAttributeSummary>(response)
  },
  removePrivateAttributes: async (projectUid: string) => {
    const response = await post(
      `projects/project/${projectUid}/remove_private_attributes`,
    )
    return await parseJsonResponse<PrivateAttributeSummary>(response)
  },
  clearSeed: async (projectUid: string) => {
    const response = await post(`projects/project/${projectUid}/clear_seed`)
    return await parseJsonResponse<Project>(response)
  },
  getValidation: async (projectUid: string) => {
    const response = await get(`projects/project/${projectUid}/validation`)
    return await parseJsonResponse<ProjectValidation>(response)
  },
  validateProject: async (projectUid: string) => {
    return await post(`projects/project/${projectUid}/validate`)
  },
}

export default projectApi
