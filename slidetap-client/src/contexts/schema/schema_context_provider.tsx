import { useQuery } from '@tanstack/react-query'
import React from 'react'
import schemaApi from 'src/services/api/schema_api'

import Skeleton from '@mui/material/Skeleton'
import { SchemaContext } from './schema_context'

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
