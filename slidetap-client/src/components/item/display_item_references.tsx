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
import type { ItemRelation, ItemSchema } from 'models/schema'
import DisplayItemReferencesOfType from './reference/display_references_by_type'

interface DisplayItemReferencesProps {
  action: Action
  relations: Array<{ relation: ItemRelation; schema: ItemSchema }>
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplayItemReferences({
  action,
  relations,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplayItemReferencesProps): React.ReactElement {
  const referencesBySchema: Record<string, ItemReference[]> = {}
  relations.forEach((relation) => {
    referencesBySchema[relation.schema.uid] = references.filter(
      (reference) => reference.schemaUid === relation.schema.uid,
    )
  })
  return (
    <Stack direction="column" spacing={1}>
      {relations.map((relation) => (
        <DisplayItemReferencesOfType
          key={relation.relation.uid}
          title={relation.relation.name}
          editable={action !== Action.VIEW}
          schemaUid={relation.schema.uid}
          schemaDisplayName={relation.schema.displayName}
          references={referencesBySchema[relation.schema.uid]}
          projectUid={projectUid}
          handleItemOpen={handleItemOpen}
          handleItemReferencesUpdate={handleItemReferencesUpdate}
        />
      ))}
    </Stack>
  )
}
