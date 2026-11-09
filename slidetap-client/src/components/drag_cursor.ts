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

/** An open hand, the outline of the Material "pan tool" icon. */
const HAND_PATH =
  'M23 5.5V20c0 2.2-1.8 4-4 4h-7.3c-1.08 0-2.1-.43-2.85-1.19L1 14.83s1.26-1.23 ' +
  '1.3-1.25c.22-.19.49-.29.79-.29.22 0 .42.06.6.16.04.01 4.31 2.46 4.31 2.46V4c0' +
  '-.83.67-1.5 1.5-1.5S11 3.17 11 4v7h1V1.5c0-.83.67-1.5 1.5-1.5S15 .67 15 1.5V11' +
  'h1V2.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5V11h1V5.5c0-.83.67-1.5 1.5-1.5s1.5' +
  '.67 1.5 1.5z'

/** A white hand edged in black, as a cursor. */
const HAND = (() => {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" ` +
    `viewBox="-1.5 -1.5 27 27"><path d="${HAND_PATH}" fill="#ffffff" ` +
    `stroke="#000000" stroke-width="2" paint-order="stroke" ` +
    `stroke-linejoin="round"/></svg>`
  return `url("data:image/svg+xml,${encodeURIComponent(svg)}") 11 11`
})()

/** The cursor of a drag handle: a white hand edged in black, which reads on a
 * light background and a dark one alike.
 *
 * The browser's own hand is drawn by the system, which on Windows is white
 * with no edge, and is lost on a light background. The browser's own is kept
 * as the fallback. */
export const dragHandleCursor = {
  cursor: `${HAND}, grab`,
  '&:active': { cursor: `${HAND}, grabbing` },
}
