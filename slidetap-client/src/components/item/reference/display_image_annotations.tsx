import React from 'react'

import { Stack } from '@mui/material'
import type { ItemReference } from 'models/item'
import type { AnnotationToImageRelation } from 'models/schema'
import { Action } from 'models/table_item'
import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplayImageAnnotationsProps {
  action: Action
  relations: AnnotationToImageRelation[]
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplayImageAnnotations({
  action,
  relations,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplayImageAnnotationsProps): React.ReactElement {
  if (relations.length === 0) {
    return <></>
  }
  const referencesByRelation: Record<string, ItemReference[]> = {}
  relations.forEach((relation) => {
    referencesByRelation[relation.uid] = references.filter(
      (reference) => reference.schemaUid === relation.annotation.uid,
    )
  })
  return (
    <Stack direction="column" spacing={1}>
      {relations.map((relation) => (
        <DisplayItemReferencesOfType
          key={relation.uid}
          title={relation.name}
          editable={action !== Action.VIEW}
          schemaUid={relation.annotation.uid}
          schemaDisplayName={relation.annotation.displayName}
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
