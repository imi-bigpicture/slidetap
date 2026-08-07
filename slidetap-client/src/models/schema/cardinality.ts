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
 * How many items a relation allows on one side of itself.
 *
 * Named for the multiplicity rather than for its bounds: a minimum of zero or
 * one, and a maximum of one or unbounded, is the whole space this domain asks
 * for.
 */
export enum Cardinality {
  /** Exactly one — 1..1. */
  One = 'one',
  /** At most one — 0..1. */
  ZeroOrOne = 'zero_or_one',
  /** At least one — 1..*. */
  OneOrMore = 'one_or_more',
  /** Any number, none included — 0..*. */
  ZeroOrMore = 'zero_or_more',
}

/** At least one is needed. */
export function isRequired(cardinality: Cardinality): boolean {
  return cardinality === Cardinality.One || cardinality === Cardinality.OneOrMore
}

/** More than one is permitted. */
export function allowsMultiple(cardinality: Cardinality): boolean {
  return (
    cardinality === Cardinality.OneOrMore || cardinality === Cardinality.ZeroOrMore
  )
}

/** Fewest allowed, for a field that marks too few as an error. */
export function minReferences(cardinality: Cardinality): number {
  return isRequired(cardinality) ? 1 : 0
}

/** Most allowed, or null where there is no ceiling. */
export function maxReferences(cardinality: Cardinality): number | null {
  return allowsMultiple(cardinality) ? null : 1
}
