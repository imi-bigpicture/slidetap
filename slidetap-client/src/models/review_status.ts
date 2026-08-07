//    Copyright 2024 SECTRA AB
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

/**
 * Where an item stands in review.
 *
 * One value rather than a flagged and a reviewed flag: an item leaves
 * `Flagged` only by being reviewed, so "flagged and reviewed" is not a state
 * the workflow can reach.
 */
export enum ReviewStatus {
  NotReviewed = 'not_reviewed',
  /** Something asked for review — a user, the import, or an invalid item found
   * under it at import. Whatever raised it, only a user clears it. */
  Flagged = 'flagged',
  /** Looked at and accepted. May be flagged again by a later import. */
  Reviewed = 'reviewed',
}

export const ReviewStatusStrings: Record<ReviewStatus, string> = {
  [ReviewStatus.NotReviewed]: 'Not reviewed',
  [ReviewStatus.Flagged]: 'Needs review',
  [ReviewStatus.Reviewed]: 'Reviewed',
}
