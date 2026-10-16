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

import type { RootSchema } from 'src/models/schema/root_schema'

/** What the schema calls a kind of item. */
export function schemaName(schema: RootSchema, schemaUid: string): string {
  const itemSchema =
    schema.samples[schemaUid] ??
    schema.images[schemaUid] ??
    schema.observations[schemaUid] ??
    schema.annotations[schemaUid]
  return itemSchema?.displayName ?? 'Item'
}
