export function snakeCase2TitleCase(tag: string): string {
  return tag
    .replace(/^[-_]*(.)/, (_, c) => c.toUpperCase())
    .replace(/[-_]+(.)/g, (_, c) => ' ' + String(c).toUpperCase())
}
