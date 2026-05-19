//    Copyright 2026 SECTRA AB
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

import { createContext, useContext, type ReactElement, type ReactNode } from 'react'
import type { Batch } from 'src/models/batch'
import type { Project } from 'src/models/project'

/**
 * A single flavor-provided page mounted under /project/:projectUid/*.
 *
 * Each page registers exactly one route and exactly one sidebar entry —
 * the two are tied together so paths cannot drift.
 */
export interface ProjectPage {
  /**
   * Path relative to the project root, without a leading slash
   * (e.g. "landing-page"). Must not collide with built-in paths such as
   * "settings", "dataset", "batches", "export", etc.
   */
  path: string

  /** Component rendered when the route matches. */
  element: ReactElement

  /** Label shown in the sidebar. */
  label: string

  /** Icon shown in the sidebar. */
  icon: ReactNode

  /** Optional tooltip / description in the sidebar. */
  description?: string

  /**
   * Gates whether the sidebar entry is clickable. Defaults to true. Pass a
   * predicate to gate on runtime state — same lifecycle objects the
   * built-in entries use (e.g. Export only enables when the project is
   * COMPLETED).
   *
   * Note: this gates only the sidebar entry. The route itself remains
   * mounted, so a user can still reach the page via URL or refresh. Treat
   * this as a UX hint, not a security boundary.
   */
  enabled?: boolean | ((project: Project, batch: Batch) => boolean)
}

/**
 * A grouped collection of flavor pages, rendered as a section in the
 * project sidebar.
 */
export interface ProjectSection {
  /** Section header (e.g. "BigPicture"). */
  title: string

  /** Pages in this section, in display order. */
  pages: ProjectPage[]
}

/**
 * Extension points for flavor-specific applications that wrap the SlideTap
 * client (e.g. a BigPicture frontend that adds a landing-page editor).
 *
 * Tip: declare the AppExtensions object at module scope so its reference
 * identity is stable across renders. Inlining it in a re-rendering
 * component triggers extra renders in every consumer of useExtensions().
 */
export interface AppExtensions {
  /**
   * Extra sections added to the project sidebar, appended after the
   * built-in Project and Batch sections. Each section's pages contribute
   * both a sidebar entry and a route under /project/:projectUid/*.
   */
  projectSections?: ProjectSection[]
}

export const ExtensionsContext = createContext<AppExtensions>({})

export function useExtensions(): AppExtensions {
  return useContext(ExtensionsContext)
}

/**
 * Validates a single extension page path against the built-in paths and any
 * paths already seen in the current pass. Throws on rule violation.
 *
 * Mutates `seen` by adding the path on success.
 */
export function assertExtensionPath(
  path: string,
  reserved: ReadonlySet<string>,
  seen: Set<string>,
): void {
  if (path.startsWith('/')) {
    throw new Error(
      `Extension project page path must not start with "/" (got "${path}")`,
    )
  }
  if (reserved.has(path)) {
    throw new Error(
      `Extension project page path "${path}" collides with a built-in route`,
    )
  }
  if (seen.has(path)) {
    throw new Error(`Duplicate extension project page path "${path}"`)
  }
  seen.add(path)
}
