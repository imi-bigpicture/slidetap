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

import type { AttributeFilter, RelationFilter } from 'src/models/table_item'

/** What the verifier last decided about a drawn unit. */
export enum VerificationVerdict {
  Pending = 'pending',
  Passed = 'passed',
  Failed = 'failed',
}

/** Where a drawn unit stands, read from its verdict and from what has happened
 * to the unit since. */
export enum VerificationState {
  Pending = 'pending',
  Passed = 'passed',
  /** Failed, and neither checked again nor taken out of the project since. */
  Failed = 'failed',
  /** Decided on, and something under it was saved afterwards. */
  NeedsRecheck = 'needs_recheck',
  /** Taken out of the project after it was drawn. */
  Removed = 'removed',
}

export const VerificationStateStrings: Record<VerificationState, string> = {
  [VerificationState.Pending]: 'Not verified',
  [VerificationState.Passed]: 'Passed',
  [VerificationState.Failed]: 'Failed',
  [VerificationState.NeedsRecheck]: 'Changed since decided',
  [VerificationState.Removed]: 'Taken out',
}

/** Which units of the batch a round is drawn from, as the item tables filter
 * them. Empty is every unit of the batch. */
export interface VerificationPopulation {
  attributeFilters: AttributeFilter[] | null
  relationFilters: RelationFilter[] | null
}

/** A draw to make. A size or a fraction, and the policy's suggestion where
 * neither is given. */
export interface VerificationRoundCreate {
  size?: number
  fraction?: number
  population?: VerificationPopulation
  originEntryUid?: string
}

/** One draw of units of a batch to verify, and how it is going. */
export interface VerificationRound {
  uid: string
  batchUid: string
  /** Its place among the rounds of the batch, from one. */
  number: number
  createdAt: string
  /** The random seed it was drawn with, picked by the server. With the units
   * it was drawn from, it tells which units it drew. */
  seed: number
  /** How many were asked for; null where a fraction or nothing was. */
  requestedSize: number | null
  /** What share was asked for; null where a size or nothing was. */
  requestedFraction: number | null
  /** How the units it was drawn from were filtered; null for all of them. */
  population: VerificationPopulation | null
  /** How many units it was drawn from. */
  populationSize: number
  /** The entry whose failure the round follows up on, where it does. */
  originEntryUid: string | null
  /** How many units it drew. */
  drawn: number
  /** How many of those have been decided on at least once. */
  decided: number
  /** How many failed at least once, fixed since or not. */
  failed: number
  /** Whether more failed than the policy warns at. */
  failureRateExceeded: boolean
}

/** A unit drawn for verification: what was last decided, `verdict`, and
 * where that leaves the unit now, `state`. */
export interface VerificationEntry {
  uid: string
  roundUid: string
  /** The `number` of the round that drew it. */
  roundNumber: number
  /** The review unit drawn. */
  unitUid: string
  identifier: string
  pseudonym: string | null
  verdict: VerificationVerdict
  state: VerificationState
  /** Why it failed, kept after it passes again. */
  reason: string | null
  /** When it was last decided on; null while pending. */
  decidedAt: string | null
  /** When it first failed, kept after it passes again. */
  failedAt: string | null
  /** When anything in or under the unit last changed, however it was
   * changed. */
  lastChanged: string | null
}

/** What a verifier decided about a drawn unit. A reason is needed to fail it. */
export interface VerificationDecision {
  verdict: VerificationVerdict.Passed | VerificationVerdict.Failed
  reason?: string
}

/** Which part of a policy a suggested draw size comes from. */
export enum VerificationSuggestionBasis {
  /** The smallest sample in which no failures shows the defect rate is low
   * enough with the confidence asked for. */
  Targets = 'targets',
  Size = 'size',
  Fraction = 'fraction',
  Minimum = 'minimum',
}

/** How many units a draw offers to take, and what that number comes from. */
export interface VerificationSuggestion {
  /** What is offered: `wanted`, raised to the minimum and limited to what is
   * left to draw. */
  size: number
  basis: VerificationSuggestionBasis
  /** What the basis asks for, before the minimum and what is left apply. */
  wanted: number
  /** How many units are left to draw. */
  undrawn: number
  /** The fewest a draw takes; with a required policy, also what has to be
   * drawn and decided before the batch can be completed. */
  minimumSize: number
  targetConfidence: number | null
  targetDefectRate: number | null
  fraction: number | null
}

/** How verifying a batch stands. */
export interface BatchVerification {
  batchUid: string
  /** False where the root of the project declares no verification policy. */
  verified: boolean
  required: boolean
  /** How many units of the batch are in the project. */
  populationSize: number
  /** How many of those no round has drawn yet. */
  undrawn: number
  /** How many a whole-batch draw would take of what is undrawn, and why; null
   * where the batch is not verified. */
  suggestion: VerificationSuggestion | null
  rounds: VerificationRound[]
  entries: VerificationEntry[]
  /** Why the batch cannot be completed yet, as far as verifying goes. */
  blocking: string[]
}
