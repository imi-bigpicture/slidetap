/**
 * Get the display identifier for an item based on pseudonym mode.
 *
 * When pseudonym mode is off, returns the item's identifier.
 * When on, returns the stored pseudonym, or a stable fallback
 * derived from the item's UID (matching the backend computation).
 */
export function getDisplayIdentifier(
  item: { uid: string; identifier: string; pseudonym: string | null },
  pseudonymMode: boolean,
): string {
  if (!pseudonymMode) {
    return item.identifier
  }
  return item.pseudonym ?? 'ANON-' + item.uid.substring(0, 8).toUpperCase()
}
