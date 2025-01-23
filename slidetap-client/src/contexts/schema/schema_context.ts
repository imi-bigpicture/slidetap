import React from 'react'
import { RootSchema } from 'src/models/schema/root_schema'

export const SchemaContext = React.createContext<RootSchema | undefined>(undefined)

export const useSchemaContext = () => {
    const schema = React.useContext(SchemaContext)
    if (schema === undefined) {
        throw new Error('useSchemaContext must be used within a SchemaContextProvider')
    }
    return schema
}