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

/** A private attribute schema that some owner in the dataset holds. */
export interface PrivateAttributeKind {
  /** Display name of the item schema, or of the dataset, holding it. */
  owner: string
  /** Display name of the attribute schema. */
  attribute: string
}

/** Mirrors `slidetap.model.PrivateAttributeSummary`. Never carries values. */
export interface PrivateAttributeSummary {
  attributes: PrivateAttributeKind[]
}
