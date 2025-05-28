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

import { Button, TextField } from '@mui/material'
import Grid from '@mui/material/Grid2'
import { useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import AttributeDetails from 'src/components/attribute/attribute_details'
import { Action } from 'src/models/action'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { Dataset } from 'src/models/dataset'
import datasetApi from 'src/services/api/dataset_api'
import { useSchemaContext } from '../../contexts/schema/schema_context'

interface DatasetSettingsProps {
  dataset: Dataset
}

export default function DatasetSettings({
  dataset,
}: DatasetSettingsProps): ReactElement {
  const queryClient = useQueryClient()
  const rootSchema = useSchemaContext()
  const handleUpdateDataset = (): void => {
    datasetApi
      .update(dataset)
      .then((updatedDataset) => {
        queryClient.setQueryData(['dataset', dataset.uid], updatedDataset)
      })
      .catch((x) => {
        console.error('Failed to update dataset', x)
      })
  }

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const { value } = event.target
    queryClient.setQueryData(['dataset', dataset.uid], {
      ...dataset,
      name: value,
    })
  }

  const baseHandleAttributeUpdate = (
    tag: string,
    attribute: Attribute<AttributeValueTypes>,
  ): void => {
    const updatedAttributes = { ...dataset.attributes }
    updatedAttributes[tag] = attribute
    const updatedDataset = { ...dataset, attributes: updatedAttributes }
    queryClient.setQueryData(['dataset', dataset.uid], updatedDataset)
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid size={{ xs: 2 }}>
        <TextField
          label="Dataset Name"
          variant="standard"
          onChange={handleNameChange}
          defaultValue={dataset.name}
          autoFocus
        />
      </Grid>
      <Grid size={{ xs: 6 }}>
        <AttributeDetails
          schemas={rootSchema?.dataset.attributes ?? {}}
          attributes={dataset.attributes}
          action={Action.EDIT}
          handleAttributeOpen={() => {}}
          handleAttributeUpdate={baseHandleAttributeUpdate}
        />
      </Grid>
      <Grid size={{ xs: 12 }}>
        <Button onClick={handleUpdateDataset}>Update</Button>
      </Grid>
    </Grid>
  )
}
