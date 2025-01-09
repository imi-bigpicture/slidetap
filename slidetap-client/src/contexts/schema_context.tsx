import { useQuery } from '@tanstack/react-query'
import { RootSchema } from 'models/schema/root_schema'
import React from 'react'
import schemaApi from 'services/api/schema_api'

import Skeleton from '@mui/material/Skeleton'

const SchemaContext = React.createContext<RootSchema | undefined>(undefined)

export const useSchemaContext = () => {
  const schema = React.useContext(SchemaContext)
  if (schema === undefined) {
    throw new Error('useSchemaContext must be used within a SchemaContextProvider')
  }
  return schema
}

export const SchemaContextProvider = ({ children }: { children: React.ReactNode }) => {
  const schemaQuery = useQuery({
    queryKey: ['schema'],
    queryFn: async () => {
      return schemaApi.getRootSchema()
    },
  })

  if (schemaQuery.isPending) {
    return <Skeleton />
  }

  if (schemaQuery.isError || schemaQuery.data === undefined) {
    throw schemaQuery.error
  }

  return (
    <SchemaContext.Provider value={schemaQuery.data}>{children}</SchemaContext.Provider>
  )
}
