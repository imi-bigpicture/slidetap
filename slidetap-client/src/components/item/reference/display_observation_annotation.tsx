import React from 'react'

import { Stack } from '@mui/material'
import { Action } from 'models/action'
import type { ItemReference } from 'models/item'
import type { ObservationToAnnotationRelation } from 'models/schema'

import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplayObservationAnnotationProps {
  action: Action
  relation: ObservationToAnnotationRelation
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplayObservationAnnotation({
  action,
  relation,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplayObservationAnnotationProps): React.ReactElement {
  return (
    <Stack direction="column" spacing={1}>
      <DisplayItemReferencesOfType
        key={relation.uid}
        title={relation.name}
        editable={action !== Action.VIEW}
        schemaUid={relation.annotation.uid}
        schemaDisplayName={relation.annotation.displayName}
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
