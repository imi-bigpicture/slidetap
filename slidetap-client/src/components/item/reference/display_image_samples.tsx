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

import { Stack } from '@mui/material'
import React from 'react'
import { ItemDetailAction } from 'src/models/action'
import { maxReferences, minReferences } from 'src/models/schema/cardinality'
import { useSchemaContext } from '../../../contexts/schema/schema_context'
import DisplayItemReferencesOfType from './display_references_by_type'

interface DisplayImageSamplesProps {
  action: ItemDetailAction
  schemaUid: string
  references: Record<string, string[]>
  datasetUid: string
  batchUid: string | null
  handleItemOpen: (name: string, uid: string, pseudonym?: string | null) => void
  handleItemReferencesUpdate: (schema_uid: string, references: string[]) => void
}

export default function DisplayImageSamples({
  action,
  schemaUid,
  references,
  datasetUid,
  batchUid,
  handleItemOpen,
  handleItemReferencesUpdate,
}: DisplayImageSamplesProps): React.ReactElement {
  const rootSchema = useSchemaContext()
  const relations = rootSchema.images[schemaUid].samples
  return (
    <Stack direction="column" spacing={1}>
      {relations.map((relation) => (
        <DisplayItemReferencesOfType
          key={relation.uid}
          title={relation.sampleTitle}
          editable={action !== ItemDetailAction.VIEW}
          schema={rootSchema.samples[relation.sampleUid]}
          references={references[relation.sampleUid] || []}
          datasetUid={datasetUid}
          batchUid={batchUid}
          handleItemOpen={handleItemOpen}
          handleItemReferencesUpdate={(refernces) =>
            handleItemReferencesUpdate(relation.sampleUid, refernces)
          }
          // An orphan relation asks for nothing: an image left off it is the
          // normal case, and one parked on it is already invalid for being
          // there. Marking the empty field red would call every correctly
          // matched image a problem.
          minReferences={relation.orphan ? 0 : minReferences(relation.samples)}
          maxReferences={maxReferences(relation.samples)}
        />
      ))}
    </Stack>
  )
}
