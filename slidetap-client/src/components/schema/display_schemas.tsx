import React, { useEffect, useState, type ReactElement } from 'react'
import { Table } from 'components/table'
import type { AttributeSchema } from 'models/schema'
import schemaApi from 'services/api/schema_api'

const rootSchemaUid = 'be6232ba-76fe-40d8-af4a-76a29eb85b3a'

export default function DisplaySchemas(): ReactElement {
  const [schemas, setSchemas] = useState<AttributeSchema[]>([])
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const getSchemas = (): void => {
    schemaApi
      .getAttributeSchemas(rootSchemaUid)
      .then((schemas) => {
        setSchemas(schemas)
        setIsLoading(false)
      })
      .catch((x) => {
        console.error('Failed to get schemas', x)
      })
  }

  useEffect(() => {
    getSchemas()
  }, [])

  return (
    <React.Fragment>
      <Table
        columns={[
          {
            header: 'Name',
            accessorKey: 'name',
          },
          {
            header: 'Attribute',
            accessorKey: 'attributeSchemaName',
          },
        ]}
        data={schemas.map((schema) => {
          return {
            uid: schema.uid,
            name: schema.displayName,
          }
        })}
        rowsSelectable={false}
        isLoading={isLoading}
      />
    </React.Fragment>
  )
}
