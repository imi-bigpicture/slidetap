import { Project } from 'models/project'
import { ImageTableItem, ItemTableItem } from 'models/table_item'

import { post, get, postFile } from 'services/api/api_methods'

const projectApi = {

    create: async (name: string) => {
        return await post('project/create', { name })
            .then<Project>(async response => await response.json())
    },

    update: async (project: Project) => {
        return await post(
            `project/${project.uid}/update`,
            { name: project.name }
        )
    },

    get: async (projectUid: string) => {
        return await get(`project/${projectUid}/status`)
            .then<Project>(async response => await response.json())
    },

    getView: async (projectUid: string, view: string) => {
        return await get(`project/${projectUid}/select/${view}`)
            .then<Project>(async response => await response.json())
    },

    getProjects: async () => {
        return await get('project')
            .then<Project[]>(async response => await response.json())
    },

    delete: async (
        projectUid: string
    ) => {
        return await post(`project/${projectUid}/delete`)
    },

    uploadProjectFile: async (
        projectUid: string,
        file: File
    ) => {
        return await postFile(`project/${projectUid}/uploadFile`, file)
    },

    getCount: async (
        projectUid: string,
        itemSchemaUid: string,
        selected?: boolean
    ) => {
        const path = `project/${projectUid}/items/${itemSchemaUid}/count`
        const args: Map<string, string> = new Map()
        if (selected !== undefined) {
            args.set('selected', selected.toString())
        }
        return await get(path, args)
            .then<number>(async response => await response.json())
    },

    getItems: async (
        projectUid: string,
        itemSchemaUid: string,
        included?: boolean,
        excluded?: boolean
    ) => {
        const path = `project/${projectUid}/items/${itemSchemaUid}`
        const args: Map<string, string> = new Map()
        if (included !== undefined) {
            args.set('included', included.toString())
        }
        if (excluded !== undefined) {
            args.set('excluded', excluded.toString())
        }
        return await get(path, args)
            .then<ItemTableItem[]>(async response => await response.json())
    },

    getImages: async (
        projectUid: string,
        itemSchemaUid: string,
        included?: boolean,
        excluded?: boolean
    ) => {
        const path = `project/${projectUid}/items/${itemSchemaUid}`
        const args: Map<string, string> = new Map()
        if (included !== undefined) {
            args.set('included', included.toString())
        }
        if (excluded !== undefined) {
            args.set('excluded', excluded.toString())
        }
        return await get(path, args)
            .then<ImageTableItem[]>(async response => await response.json())
    },

    selectItem: async (
        projectUid: string,
        itemUid: string,
        value: boolean
    ) => {
        return await post(
            `project/${projectUid}/item/${itemUid}/select?value=${value.toString()}`
        )
    },

    start: async (
        projectUid: string
    ) => {
        return await post(`project/${projectUid}/start`)
    },

    submit: async (
        projectUid: string
    ) => {
        return await post(`project/${projectUid}/submit`)
    }
}

export default projectApi
