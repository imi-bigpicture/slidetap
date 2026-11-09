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

/**
 * The items of a schema grouped by values they share, each group to hold at
 * least a number of something, such as patients. Declared by the application;
 * what an item is grouped by is worked out on the server.
 */
export interface ItemGroupingPolicy {
  /** The item schema whose items are grouped. */
  schemaUid: string
  /** The fewest a group is to hold of what is counted. */
  minimumCount: number
  /** The most a group can hold and still be shown as close to the minimum.
   * Null where no group is shown as close. */
  closeCount: number | null
  /** What is counted in a group, as shown, e.g. "Patients". */
  countDisplayName: string
  /** What the groups are called where they are listed. */
  displayName: string
}
