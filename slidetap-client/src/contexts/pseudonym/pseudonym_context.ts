import { createContext, useContext } from 'react'

interface PseudonymContextType {
  pseudonymMode: boolean
  togglePseudonymMode: () => void
}

export const PseudonymContext = createContext<PseudonymContextType | undefined>(undefined)

export function usePseudonym(): PseudonymContextType {
  const context = useContext(PseudonymContext)
  if (context === undefined) {
    throw new Error('usePseudonym must be used within a PseudonymProvider')
  }
  return context
}
