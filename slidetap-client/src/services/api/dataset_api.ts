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

import type { Dataset } from 'src/models/dataset'

import { get } from 'src/services/api/api_methods'

const datasetApi = {
    // import: async(dataset: Dataset) => {
    //     return await post('dataset/import', dataset).then<Dataset>(
    //     async (response) => await response.json(),
    //     )
    // },

    // getImportable: async () => {
    //     return await get('dataset/importable').then<Dataset[]>(
    //         async (response) => await response.json(),
    //   )
    // },

    // getDatasets: async () => {
    //     return await get('dataset').then<Dataset[]>(
    //         async (response) => await response.json(),
    //     )
    // },

    // delete: async (datasetUid: string) => {
    //     return await del(`dataset/${datasetUid}`)
    // },

    // update: async (dataset: Dataset) => {
    //     return await post(`dataset/${dataset.uid}`, dataset).then<Dataset>(
    //       async (response) => await response.json())
    // },
    get: async (datasetUid: string) => {
        return await get(`datasets/dataset/${datasetUid}`).then<Dataset>(
            async (response) => await response.json(),
        )
    },
}

export default datasetApi
