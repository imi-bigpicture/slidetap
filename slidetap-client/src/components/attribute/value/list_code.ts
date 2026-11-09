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

import type { CodeAttribute } from 'src/models/attribute'

/** A code of a list as the list holds it after an edit, reading as the server
 * writes it back on save.
 *
 * The server settles the display value when the item is saved. Until then the
 * list, and whatever shows the list rather than its codes, would go on reading
 * what the code said before it was edited.
 */
export function withCodeDisplayValue(child: CodeAttribute): CodeAttribute {
  if (child.updatedValue !== null) {
    return { ...child, displayValue: child.updatedValue.meaning }
  }
  return { ...child, displayValue: child.mappableValue ?? '' }
}
