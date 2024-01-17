import React from 'react'

import { Stack } from '@mui/material'
import type { ItemReference } from 'models/item'
import type { ObservationToSampleRelation } from 'models/schema'
import { Action } from 'models/table_item'
import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplaySampleObservationsProps {
  action: Action
  relations: ObservationToSampleRelation[]
  references: ItemReference[]
  projectUid: string
  handleItemOpen: (itemUid: string) => void
  handleItemReferencesUpdate: (references: ItemReference[]) => void
}

export default function DisplaySampleObservations({
  action,
  relations,
  references,
  projectUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplaySampleObservationsProps): React.ReactElement {
  if (relations.length === 0) {
    return <></>
  }
  const referencesByRelation: Record<string, ItemReference[]> = {}
  relations.forEach((relation) => {
    referencesByRelation[relation.uid] = references.filter(
      (reference) => reference.schemaUid === relation.observation.uid,
    )
  })
  return (
    <Stack direction="column" spacing={1}>
      {relations.map((relation) => (
        <DisplayItemReferencesOfType
          key={relation.uid}
          title={relation.name}
          editable={action !== Action.VIEW}
          schemaUid={relation.observation.uid}
          schemaDisplayName={relation.observation.displayName}
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
