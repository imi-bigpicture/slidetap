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

import {
  VerificationSuggestionBasis,
  type VerificationSuggestion,
} from 'src/models/verification'

/** Whole percent where it is one, otherwise to one decimal. */
function percent(share: number): string {
  const value = Math.round(share * 1000) / 10
  return `${value}%`
}

function units(count: number): string {
  return `${count} unit${count === 1 ? '' : 's'}`
}

/** Why the policy suggests drawing as many as it does, in words. */
export function suggestionReason(suggestion: VerificationSuggestion): string {
  let reason: string
  switch (suggestion.basis) {
    case VerificationSuggestionBasis.Targets:
      reason =
        `To be ${percent(suggestion.targetConfidence ?? 0)} sure that at most ` +
        `${percent(suggestion.targetDefectRate ?? 0)} of units are wrong, ` +
        `${units(suggestion.wanted)} need to pass without a failure.`
      break
    case VerificationSuggestionBasis.Fraction:
      reason =
        `The project draws ${percent(suggestion.fraction ?? 0)} of what is left, ` +
        `${units(suggestion.wanted)}.`
      break
    case VerificationSuggestionBasis.Size:
      reason = `The project draws ${units(suggestion.wanted)} at a time.`
      break
    default:
      reason = `The project draws at least ${units(suggestion.minimumSize)}.`
  }
  if (suggestion.size < suggestion.wanted) {
    reason +=
      suggestion.size === suggestion.undrawn
        ? ` Only ${suggestion.undrawn} ${suggestion.undrawn === 1 ? 'is' : 'are'} left to draw, so all of them are suggested.`
        : ` Suggested: ${suggestion.size}.`
  } else if (suggestion.size > suggestion.wanted) {
    reason += ` The project draws at least ${units(suggestion.minimumSize)}, so ${suggestion.size} are suggested.`
  } else if (suggestion.basis !== VerificationSuggestionBasis.Minimum) {
    reason += ` Suggested: ${suggestion.size} of ${suggestion.undrawn}.`
  }
  return reason
}
