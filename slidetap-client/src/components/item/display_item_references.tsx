import React, { type ReactElement } from 'react'

import type { ItemReference } from 'models/items'
import { Card, CardContent, Link, CardHeader } from '@mui/material'

interface DisplayItemReferencesProps {
  title: string
  references: ItemReference[]
  handleItemOpen: (itemUid: string) => void
}

export default function DisplayItemReferences({
  title,
  references,
  handleItemOpen,
}: DisplayItemReferencesProps): ReactElement {
  if (references.length === 0) {
    return <></>
  }
  return (
    <Card>
      <CardHeader title={title} />
      <CardContent>
        {references.map((reference) => (
          <Link
            key={reference.uid}
            onClick={() => {
              handleItemOpen(reference.uid)
            }}
          >
            {reference.schemaDisplayName} - {reference.name}
          </Link>
        ))}
      </CardContent>
    </Card>
  )
}
