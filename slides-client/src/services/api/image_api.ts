import { Dzi } from 'models/dzi'
import { Image } from 'models/items'

import { get } from 'services/api/api_methods'

const imageApi = {

    getImagesWithThumbnail: async (
        projectUid: string
    ) => {
        return await get('image/thumbnails/' + projectUid)
            .then<Image[]>(async response => await response.json())
    },

    getThumbnail: async (
        imageUid: string,
        size: [width: number, height: number]
    ) => {
        const path = 'image/' + imageUid + '/thumbnail'
        const args: Map<string, string> = new Map()
        args.set('width', size[0].toString())
        args.set('height', size[1].toString())
        return await get(path, args)
            .then<Blob>(async response => await response.blob())
    },

    getDzi: async (
        imageUid: string
    ) => {
        return await get('image/' + imageUid)
            .then<Dzi>(async response => await response.json())
    },

    getTile: async (
        projectUid: string,
        imageUid: string,
        level: number,
        x: number,
        y: number,
        extension: string
    ) => {
        const path = 'image/' + imageUid + '/' + level.toString() +
            '/' + x.toString() + '_' + y.toString() + '.' + extension
        return await get(path)
            .then<Blob>(async response => await response.blob())
    }
}

export default imageApi
