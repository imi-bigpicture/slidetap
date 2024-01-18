import React from 'react'

import { Stack } from '@mui/material'
import type { ItemReference } from 'models/item'
import type { ObservationToSampleRelation } from 'models/schema'
import { Action } from 'models/table_item'
import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplayObservationSampleProps {
  action: Action
  relation: ObservationToSampleRelation
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplayObservationSample({
  action,
  relation,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplayObservationSampleProps): React.ReactElement {
  console.log(references, relation)
  return (
    <Stack direction="column" spacing={1}>
      <DisplayItemReferencesOfType
        key={relation.uid}
        title={relation.name}
        editable={action !== Action.VIEW}
        schemaUid={relation.sample.uid}
        schemaDisplayName={relation.sample.displayName}
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
