import React, { useEffect, useState, type ReactNode } from 'react'
import { PseudonymContext } from './pseudonym_context'

interface PseudonymProviderProps {
  children: ReactNode
}

const PSEUDONYM_STORAGE_KEY = 'slidetap-pseudonym-mode'

export function PseudonymProvider({
  children,
}: PseudonymProviderProps): React.ReactElement {
  const [pseudonymMode, setPseudonymMode] = useState<boolean>(() => {
    return localStorage.getItem(PSEUDONYM_STORAGE_KEY) === 'true'
  })

  useEffect(() => {
    localStorage.setItem(PSEUDONYM_STORAGE_KEY, String(pseudonymMode))
  }, [pseudonymMode])

  // Sync across tabs/popup windows
  useEffect(() => {
    const onStorage = (e: StorageEvent): void => {
      if (e.key === PSEUDONYM_STORAGE_KEY) {
        setPseudonymMode(e.newValue === 'true')
      }
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const togglePseudonymMode = (): void => {
    setPseudonymMode((prev) => !prev)
  }

  return (
    <PseudonymContext.Provider value={{ pseudonymMode, togglePseudonymMode }}>
      {children}
    </PseudonymContext.Provider>
  )
}
