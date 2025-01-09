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

import { Stack } from '@mui/material'
import { Action } from 'models/action'
import React from 'react'
import { useSchemaContext } from '../../../contexts/schema_context'
import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplaySampleParentsProps {
  action: Action
  schemaUid: string
  references: string[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: string[]) => void
}

export default function DisplaySampleParents({
  action,
  schemaUid,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplaySampleParentsProps): React.ReactElement {
  const rootSchema = useSchemaContext()
  const relations = rootSchema.samples[schemaUid].parents
  console.log('sample parents', relations)
  return (
    <Stack direction="column" spacing={1}>
      {relations.map((relation) => (
        <DisplayItemReferencesOfType
          key={relation.uid}
          title={relation.parentTitle}
          editable={action !== Action.VIEW}
          schema={rootSchema.samples[relation.parentUid]}
          references={references}
          projectUid={projectUid}
          handleItemOpen={handleItemOpen}
          handleItemReferencesUpdate={handleItemReferencesUpdate}
          minReferences={relation.minParents}
          maxReferences={relation.maxParents}
        />
      ))}
    </Stack>
  )
}
