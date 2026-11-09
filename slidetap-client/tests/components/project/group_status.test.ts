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

import { describe, expect, it } from 'vitest'
import {
  GroupStatus,
  groupStatus,
  statusRanges,
} from 'src/components/project/group_status'
import type { ItemGroupSummary } from 'src/models/item_grouping'
import type { ItemGroupingPolicy } from 'src/models/schema/item_grouping_policy'

function policy(closeCount: number | null): ItemGroupingPolicy {
  return {
    schemaUid: 'specimen',
    minimumCount: 11,
    closeCount,
    countDisplayName: 'Patients',
    displayName: 'Groups',
  }
}

function group(count: number): ItemGroupSummary {
  return {
    values: [],
    parts: [],
    items: [],
    count,
    reviewUnitUids: [],
    belowMinimum: count < 11,
  }
}

describe('groupStatus', () => {
  it('says a group under the minimum is too small', () => {
    expect(groupStatus(group(10), policy(16))).toBe(GroupStatus.TOO_SMALL)
  })

  it('says a group from the minimum to the close count is close', () => {
    expect(groupStatus(group(11), policy(16))).toBe(GroupStatus.CLOSE)
    expect(groupStatus(group(16), policy(16))).toBe(GroupStatus.CLOSE)
  })

  it('says a group above the close count is large enough', () => {
    expect(groupStatus(group(17), policy(16))).toBe(GroupStatus.LARGE_ENOUGH)
  })

  it('calls no group close where the policy sets no close count', () => {
    expect(groupStatus(group(11), policy(null))).toBe(GroupStatus.LARGE_ENOUGH)
  })
})

describe('statusRanges', () => {
  it('gives each range of the policy, worst first', () => {
    expect(statusRanges(policy(16))).toEqual([
      { status: GroupStatus.TOO_SMALL, range: 'under 11' },
      { status: GroupStatus.CLOSE, range: '11-16' },
      { status: GroupStatus.LARGE_ENOUGH, range: '17 or more' },
    ])
  })

  it('leaves out the close range where the policy sets none', () => {
    expect(statusRanges(policy(null)).map((entry) => entry.status)).toEqual([
      GroupStatus.TOO_SMALL,
      GroupStatus.LARGE_ENOUGH,
    ])
  })
})
