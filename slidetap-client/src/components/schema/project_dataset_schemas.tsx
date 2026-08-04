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

import { Card, CardContent, CardHeader, Stack } from '@mui/material'
import { type ReactElement } from 'react'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { AttributeSchema } from 'src/models/schema/attribute_schema'
import SchemaChips from './schema_chips'

interface ProjectAndDatasetSchemasProps {
  openAttributeSchema: (attributeSchemaUid: string) => void
}

function toEntries(attributes: Record<string, AttributeSchema>) {
  return Object.values(attributes).map((attribute) => ({
    uid: attribute.uid,
    title: attribute.displayName,
  }))
}

/** Display the project and dataset schemas of the root schema.
 *
 * There is one of each, so they are shown side by side rather than as a table
 * of schemas to pick from. Both hold attributes without being items, so they
 * have neither an item type nor relations to other schemas.
 */
export default function ProjectAndDatasetSchemas({
  openAttributeSchema,
}: ProjectAndDatasetSchemasProps): ReactElement {
  const rootSchema = useSchemaContext()
  const schemas = [
    { type: 'Project', schema: rootSchema.project },
    { type: 'Dataset', schema: rootSchema.dataset },
  ]

  return (
    <Stack spacing={1}>
      {schemas.map(({ type, schema }) => (
        <Card key={schema.uid}>
          <CardHeader title={schema.displayName} subheader={type} />
          <CardContent>
            <Stack spacing={1}>
              <SchemaChips
                label="Attributes"
                entries={toEntries(schema.attributes)}
                onClick={openAttributeSchema}
              />
              {Object.keys(schema.privateAttributes).length > 0 && (
                <SchemaChips
                  label="Private attributes"
                  entries={toEntries(schema.privateAttributes)}
                  onClick={openAttributeSchema}
                />
              )}
            </Stack>
          </CardContent>
        </Card>
      ))}
    </Stack>
  )
}
