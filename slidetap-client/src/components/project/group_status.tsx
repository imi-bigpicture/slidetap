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
import { CheckCircleOutlined, ErrorOutlined, WarningAmber } from '@mui/icons-material'
import { type ReactElement } from 'react'
import type { ItemGroupSummary } from 'src/models/item_grouping'
import type { ItemGroupingPolicy } from 'src/models/schema/item_grouping_policy'

/** How a group stands against the minimum of its policy. */
export enum GroupStatus {
  TOO_SMALL = 'Too small',
  CLOSE = 'Close',
  LARGE_ENOUGH = 'Large enough',
}

/** How a group stands against the ranges its policy sets: under the minimum,
 * up to the count the policy still calls close, if it calls any, or above. */
export function groupStatus(
  group: ItemGroupSummary,
  policy: ItemGroupingPolicy,
): GroupStatus {
  if (group.belowMinimum) return GroupStatus.TOO_SMALL
  if (policy.closeCount !== null && group.count <= policy.closeCount) {
    return GroupStatus.CLOSE
  }
  return GroupStatus.LARGE_ENOUGH
}

/** The ranges of the policy, as a legend says them, worst first. */
export function statusRanges(
  policy: ItemGroupingPolicy,
): Array<{ status: GroupStatus; range: string }> {
  const largeFrom = (policy.closeCount ?? policy.minimumCount - 1) + 1
  return [
    { status: GroupStatus.TOO_SMALL, range: `under ${policy.minimumCount}` },
    ...(policy.closeCount !== null
      ? [
          {
            status: GroupStatus.CLOSE,
            range:
              policy.closeCount === policy.minimumCount
                ? `${policy.minimumCount}`
                : `${policy.minimumCount}-${policy.closeCount}`,
          },
        ]
      : []),
    { status: GroupStatus.LARGE_ENOUGH, range: `${largeFrom} or more` },
  ]
}

/** Worst first, for ordering groups by how much they need looking at. */
export const STATUS_SEVERITY: Record<GroupStatus, number> = {
  [GroupStatus.TOO_SMALL]: 0,
  [GroupStatus.CLOSE]: 1,
  [GroupStatus.LARGE_ENOUGH]: 2,
}

/** The status colours of the theme, each with an icon, so that a status is
 * never told by colour alone. */
export const STATUS_DISPLAY: Record<
  GroupStatus,
  { color: 'error' | 'warning' | 'success'; icon: ReactElement }
> = {
  [GroupStatus.TOO_SMALL]: {
    color: 'error',
    icon: <ErrorOutlined fontSize="inherit" />,
  },
  [GroupStatus.CLOSE]: {
    color: 'warning',
    icon: <WarningAmber fontSize="inherit" />,
  },
  [GroupStatus.LARGE_ENOUGH]: {
    color: 'success',
    icon: <CheckCircleOutlined fontSize="inherit" />,
  },
}
