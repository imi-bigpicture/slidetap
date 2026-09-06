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

import React from 'react'

export interface TypedText {
  /** What is in the field, which is what was typed rather than what the
   * attribute holds. */
  text: string
  onChange: (text: string) => void
  /** Gives what was typed to the attribute, where it says something else. */
  onBlur: () => void
}

/** Text kept in the field it is typed in, given to the attribute on leaving it.
 *
 * Written through on every keystroke, a letter is a new item: the panel holding
 * it is drawn again, and with it every field of the item, each long text among
 * them measuring itself to settle how tall it should be. Kept here, only the
 * field being typed in is drawn, and the attribute hears once, at the end.
 *
 * Leaving the field is what a button press does before it is a button press, so
 * what was typed reaches the attribute ahead of a save.
 *
 * @param value - What the attribute says, shown until something is typed.
 * @param commit - Given what was typed, where it differs from the value.
 */
export function useTypedText(
  value: string,
  commit: (text: string) => void,
): TypedText {
  const [text, setText] = React.useState(value)
  /** The value this field was last set from. What the attribute says changes
   * under the field when the item is read again, or when the value shown is
   * switched from what was edited to what was imported, and the field follows
   * it; what the user is in the middle of typing is not disturbed by a draw. */
  const [shown, setShown] = React.useState(value)
  if (value !== shown) {
    setShown(value)
    setText(value)
  }
  return {
    text,
    onChange: setText,
    onBlur: () => {
      if (text !== value) {
        commit(text)
      }
    },
  }
}
