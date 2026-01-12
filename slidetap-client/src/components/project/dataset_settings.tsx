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

import { Button, Chip, Divider, TextField } from '@mui/material'
import Grid from '@mui/material/Grid'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import AttributeDetails from 'src/components/attribute/attribute_details'
import { ItemDetailAction } from 'src/models/action'
import type { Attribute, AttributeValueTypes } from 'src/models/attribute'
import type { Dataset } from 'src/models/dataset'
import datasetApi from 'src/services/api/dataset_api'
import { useSchemaContext } from '../../contexts/schema/schema_context'

interface DatasetSettingsProps {
  dataset: Dataset
  setDataset: (dataset: Dataset) => void
}

export default function DatasetSettings({
  dataset,
  setDataset,
}: DatasetSettingsProps): ReactElement {
  const queryClient = useQueryClient()
  const rootSchema = useSchemaContext()

  const datasetUpdateMutation = useMutation({
    mutationFn: (dataset: Dataset) => {
      return datasetApi.update(dataset)
    },
    onSuccess: (updatedDataset) => {
      queryClient.setQueryData(['dataset', dataset.uid], updatedDataset)
    },
  })

  const handleNameChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const { value } = event.target
    setDataset({
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
    setDataset(updatedDataset)
  }

  return (
    <Grid container spacing={1} justifyContent="flex-start" alignItems="flex-start">
      <Grid size={{ xs: 6 }}>
        <Divider>
          <Chip label="General" color={'primary'} size="small" variant="outlined" />
        </Divider>
        <TextField
          label="Dataset Name"
          variant="standard"
          onChange={handleNameChange}
          defaultValue={dataset.name}
          autoFocus
        />

        <Divider>
          <Chip label="Attributes" color={'primary'} size="small" variant="outlined" />
        </Divider>
        <AttributeDetails
          schemas={rootSchema?.dataset.attributes ?? {}}
          attributes={dataset.attributes}
          action={ItemDetailAction.EDIT}
          handleAttributeOpen={() => {}}
          handleAttributeUpdate={baseHandleAttributeUpdate}
        />
        <Button onClick={() => datasetUpdateMutation.mutate(dataset)}>Update</Button>
      </Grid>
    </Grid>
  )
}
