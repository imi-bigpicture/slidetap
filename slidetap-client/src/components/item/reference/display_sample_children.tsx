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

import React from 'react'

import { Stack } from '@mui/material'
import { Action } from 'models/action'
import type { ItemReference } from 'models/item'
import type { SampleToSampleRelation } from 'models/schema'

import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplaySampleChildrenProps {
  action: Action
  relations: SampleToSampleRelation[]
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplaySampleChildren({
  action,
  relations,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplaySampleChildrenProps): React.ReactElement {
  const referencesByRelation: Record<string, ItemReference[]> = {}
  relations.forEach((relation) => {
    referencesByRelation[relation.uid] = references.filter(
      (reference) => reference.schemaUid === relation.child.uid,
    )
  })
  return (
    <Stack direction="column" spacing={1}>
      {relations.map((relation) => (
        <DisplayItemReferencesOfType
          key={relation.uid}
          title={relation.name}
          editable={action !== Action.VIEW}
          schemaUid={relation.child.uid}
          schemaDisplayName={relation.child.displayName}
          references={referencesByRelation[relation.uid]}
          projectUid={projectUid}
          handleItemOpen={handleItemOpen}
          handleItemReferencesUpdate={handleItemReferencesUpdate}
          minReferences={relation.minChildren}
          maxReferences={relation.maxChildren}
        />
      ))}
    </Stack>
  )
}
