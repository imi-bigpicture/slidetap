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

/** How the server behaves, as its plugin is built. The same for the whole
 * app. */
export interface ApplicationPolicy {
  /** Whether a batch's images are pre-processed, downloaded and read, in a
   * step of their own between the curation of the search and of the
   * pre-processed batch. Where not, a batch goes from its metadata search
   * straight to the curation before conversion, and its images are
   * pre-processed as they are converted. */
  readonly preProcessesImagesSeparately: boolean
}
