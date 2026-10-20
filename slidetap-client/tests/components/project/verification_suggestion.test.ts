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
import {
  VerificationSuggestionBasis,
  type VerificationSuggestion,
} from 'src/models/verification'
import { suggestionReason } from 'src/components/project/verification_suggestion'

const targets: VerificationSuggestion = {
  size: 59,
  basis: VerificationSuggestionBasis.Targets,
  wanted: 59,
  undrawn: 400,
  minimumSize: 1,
  targetConfidence: 0.95,
  targetDefectRate: 0.05,
  fraction: null,
}

describe('suggestionReason', () => {
  it('says what the targets ask for and how much of the batch that is', () => {
    expect(suggestionReason(targets)).toBe(
      'To be 95% sure that at most 5% of units are wrong, 59 units need to pass ' +
        'without a failure. Suggested: 59 of 400.',
    )
  })

  it('says why everything is suggested when the batch is smaller than that', () => {
    expect(suggestionReason({ ...targets, size: 8, undrawn: 8 })).toBe(
      'To be 95% sure that at most 5% of units are wrong, 59 units need to pass ' +
        'without a failure. Only 8 are left to draw, so all of them are suggested.',
    )
  })

  it('says what share a fraction is', () => {
    expect(
      suggestionReason({
        ...targets,
        basis: VerificationSuggestionBasis.Fraction,
        size: 42,
        wanted: 42,
        undrawn: 412,
        targetConfidence: null,
        targetDefectRate: null,
        fraction: 0.1,
      }),
    ).toBe('The project draws 10% of what is left, 42 units. Suggested: 42 of 412.')
  })

  it('says when the minimum raises what was asked for', () => {
    expect(
      suggestionReason({
        ...targets,
        basis: VerificationSuggestionBasis.Size,
        size: 10,
        wanted: 5,
        minimumSize: 10,
        targetConfidence: null,
        targetDefectRate: null,
      }),
    ).toBe(
      'The project draws 5 units at a time. The project draws at least 10 units, ' +
        'so 10 are suggested.',
    )
  })
})
