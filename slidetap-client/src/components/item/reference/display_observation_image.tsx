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
import { ItemReference } from 'models/item_reference'
import type { ObservationToImageRelation } from 'models/schema/item_relation'

import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplayObservationImageProps {
  action: Action
  relation: ObservationToImageRelation
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplayObservationImage({
  action,
  relation,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplayObservationImageProps): React.ReactElement {
  return (
    <Stack direction="column" spacing={1}>
      <DisplayItemReferencesOfType
        key={relation.uid}
        title={relation.name}
        editable={action !== Action.VIEW}
        schemaUid={relation.image.uid}
        schemaDisplayName={relation.image.displayName}
        references={references}
        projectUid={projectUid}
        handleItemOpen={handleItemOpen}
        handleItemReferencesUpdate={handleItemReferencesUpdate}
        minReferences={1}
        maxReferences={1}
      />
    </Stack>
  )
}
