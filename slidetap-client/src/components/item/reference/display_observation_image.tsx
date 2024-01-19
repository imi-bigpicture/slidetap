import React from 'react'

import { Stack } from '@mui/material'
import { Action } from 'models/action'
import type { ItemReference } from 'models/item'
import type { ObservationToImageRelation } from 'models/schema'

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
