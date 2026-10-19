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

import { MigrationStep, type MigrationProgress } from 'src/models/migration'

/** What each step of completing a conversion is called, in its order. */
const COMPLETING_STEPS: ReadonlyArray<[MigrationStep, string]> = [
  [MigrationStep.PLANNING, 'running the conversion again'],
  [MigrationStep.WRITING, 'writing the converted entities'],
  [MigrationStep.VALIDATING, 'validating the project'],
]

/** Where planning or completing a conversion is, to show above its bar. */
export function progressText(
  title: string,
  progress: MigrationProgress | null,
  completing: boolean,
): string {
  if (progress === null) {
    return `${title}: starting.`
  }
  const counts =
    `${progress.done.toLocaleString('en-gb')} of ` +
    `${progress.total.toLocaleString('en-gb')} done.`
  const index = COMPLETING_STEPS.findIndex(([step]) => step === progress.step)
  if (!completing || index === -1) {
    return `${title}. ${counts}`
  }
  return (
    `${title}: step ${index + 1} of ${COMPLETING_STEPS.length}, ` +
    `${COMPLETING_STEPS[index][1]}. ${counts}`
  )
}

/** How much of the step is done, in percent, null until it has started. */
export function progressPercent(progress: MigrationProgress | null): number | null {
  if (progress === null) {
    return null
  }
  if (progress.total === 0) {
    return 100
  }
  return (100 * progress.done) / progress.total
}
