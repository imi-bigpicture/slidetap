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

import type { ReviewLayout } from './review_layout'

/**
 * How a sample of the review units of a batch is checked by hand before the
 * batch is completed. Declared by the application, and acted on by the server:
 * the client reads it to offer a draw and to lay out what is shown.
 */
export interface VerificationPolicy {
  /** Whether a batch must have a sample drawn and checked before it can be
   * completed. A failed unit blocks either way. */
  required: boolean
  defaultSize: number | null
  defaultFraction: number | null
  minimumSize: number
  targetConfidence: number | null
  targetDefectRate: number | null
  /** Share of failed units in a round above which drawing more is suggested. */
  failureRateWarning: number | null
  /** What the verifier is shown of a unit. The review layout where null. */
  layout: ReviewLayout | null
}
