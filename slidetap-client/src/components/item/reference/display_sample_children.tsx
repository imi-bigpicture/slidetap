import React from 'react'

import { Stack } from '@mui/material'
import type { ItemReference } from 'models/item'
import type { SampleToSampleRelation } from 'models/schema'
import { Action } from 'models/table_item'
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
  if (relations.length === 0) {
    return <></>
  }
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
