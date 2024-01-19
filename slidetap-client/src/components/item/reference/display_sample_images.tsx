import React from 'react'

import { Stack } from '@mui/material'
import { Action } from 'models/action'
import type { ItemReference } from 'models/item'
import type { ImageToSampleRelation } from 'models/schema'

import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplaySampleImagesProps {
  action: Action
  relations: ImageToSampleRelation[]
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplaySampleImages({
  action,
  relations,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplaySampleImagesProps): React.ReactElement {
  if (relations.length === 0) {
    return <></>
  }
  const referencesByRelation: Record<string, ItemReference[]> = {}
  relations.forEach((relation) => {
    referencesByRelation[relation.uid] = references.filter(
      (reference) => reference.schemaUid === relation.image.uid,
    )
  })
  return (
    <Stack direction="column" spacing={1}>
      {relations.map((relation) => (
        <DisplayItemReferencesOfType
          key={relation.uid}
          title={relation.name}
          editable={action !== Action.VIEW}
          schemaUid={relation.image.uid}
          schemaDisplayName={relation.image.displayName}
          references={referencesByRelation[relation.uid]}
          projectUid={projectUid}
          handleItemOpen={handleItemOpen}
          handleItemReferencesUpdate={handleItemReferencesUpdate}
          minReferences={1}
          maxReferences={1}
        />
      ))}
    </Stack>
  )
}
