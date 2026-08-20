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
 * What a MetadataImportInterface does not include in the MetadataSearchResult.
 *
 * A MetadataImportInterface need not produce a complete hierarchy: items may be
 * missing, and produced items may be missing attributes.
 *
 * Acted on by the server, which decides what a unit is flagged for. Here so
 * that the schema a client is handed is the schema the server holds.
 */
export interface MetadataImportCompleteness {
  /** Items whose attributes are not included in the MetadataSearchResult, by
   * item schema uid. */
  nonCompleteItems: string[]
  /** Relations that are not satisfied in the MetadataSearchResult, by relation
   * uid. */
  nonCompleteRelations: string[]
}
