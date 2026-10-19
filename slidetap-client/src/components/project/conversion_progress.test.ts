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

import { describe, expect, it } from 'vitest'
import { MigrationStep } from 'src/models/migration'
import { progressPercent, progressText } from './conversion_progress'

describe('progressText', () => {
  it('says the conversion is starting until it has progress', () => {
    expect(progressText('Planning the conversion', null, false)).toBe(
      'Planning the conversion: starting.',
    )
  })

  it('counts what planning has done', () => {
    expect(
      progressText(
        'Planning the conversion',
        { step: MigrationStep.PLANNING, done: 12000, total: 204002 },
        false,
      ),
    ).toBe('Planning the conversion. 12,000 of 204,002 done.')
  })

  it('names the step completing is on and counts it', () => {
    expect(
      progressText(
        'Completing the conversion',
        { step: MigrationStep.WRITING, done: 5, total: 10 },
        true,
      ),
    ).toBe(
      'Completing the conversion: step 2 of 3, writing the converted entities. ' +
        '5 of 10 done.',
    )
  })
})

describe('progressPercent', () => {
  it('is null until there is progress', () => {
    expect(progressPercent(null)).toBeNull()
  })

  it('is the share done', () => {
    expect(progressPercent({ step: MigrationStep.VALIDATING, done: 1, total: 4 })).toBe(
      25,
    )
  })

  it('is whole for a step with nothing to do', () => {
    expect(progressPercent({ step: MigrationStep.WRITING, done: 0, total: 0 })).toBe(
      100,
    )
  })
})
