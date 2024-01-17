import type { Project, ProjectValidation } from 'models/project'
import type { ProjectStatus } from 'models/status'
import type { ImageTableItem, ItemTableItem } from 'models/table_item'

import { get, post, postFile } from 'services/api/api_methods'

const projectApi = {
  create: async (name: string) => {
    return await post('project/create', { name }).then<Project>(
      async (response) => await response.json(),
    )
  },

  update: async (project: Project) => {
    return await post(`project/${project.uid}/update`, { name: project.name })
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
    return await postFile(`project/${projectUid}/uploadFile`, file)
  },

  getCount: async (projectUid: string, itemSchemaUid: string, selected?: boolean) => {
    const path = `project/${projectUid}/items/${itemSchemaUid}/count`
    const args = new Map<string, string>()
    if (selected !== undefined) {
      args.set('selected', selected.toString())
    }
    return await get(path, args).then<number>(async (response) => await response.json())
  },

  getItems: async (
    projectUid: string,
    itemSchemaUid: string,
    included?: boolean,
    excluded?: boolean,
  ) => {
    const path = `project/${projectUid}/items/${itemSchemaUid}`
    const args = new Map<string, string>()
    if (included !== undefined) {
      args.set('included', included.toString())
    }
    if (excluded !== undefined) {
      args.set('excluded', excluded.toString())
    }
    return await get(path, args).then<ItemTableItem[]>(
      async (response) => await response.json(),
    )
  },

  getImages: async (
    projectUid: string,
    itemSchemaUid: string,
    included?: boolean,
    excluded?: boolean,
  ) => {
    const path = `project/${projectUid}/items/${itemSchemaUid}`
    const args = new Map<string, string>()
    if (included !== undefined) {
      args.set('included', included.toString())
    }
    if (excluded !== undefined) {
      args.set('excluded', excluded.toString())
    }
    return await get(path, args).then<ImageTableItem[]>(
      async (response) => await response.json(),
    )
  },

  download: async (projectUid: string) => {
    return await post(`project/${projectUid}/download`)
  },

  process: async (projectUid: string) => {
    return await post(`project/${projectUid}/process`)
  },

  export: async (projectUid: string) => {
    return await post(`project/${projectUid}/export`)
  },
  getValidation: async (projectUid: string) => {
    return await get(`project/${projectUid}/validation`).then<ProjectValidation>(
      async (response) => await response.json(),
    )
  }
}

export default projectApi
