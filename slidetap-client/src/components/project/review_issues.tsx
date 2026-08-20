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

import { Check } from '@mui/icons-material'
import {
  Box,
  Chip,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Tooltip,
  Typography,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { type ReactElement } from 'react'
import { ReviewIssueSource } from 'src/models/review_issue'
import itemApi from 'src/services/api/item_api'
import { queryKeys } from 'src/services/query_keys'

/** What raised it, as the column says it. Shown for every kind, including the
 * ones a person raised: a list where only some rows are labelled reads as
 * though the rest are the same kind as each other. */
const SOURCE_NAMES: Record<ReviewIssueSource, string> = {
  [ReviewIssueSource.User]: 'Raised',
  [ReviewIssueSource.MetadataImporter]: 'Metadata import',
  [ReviewIssueSource.ImageImporter]: 'Image import',
  [ReviewIssueSource.Validation]: 'Not valid',
}

interface ReviewIssuesProps {
  reviewUnitUid: string
  /** The item the panel beside this one is showing, if any. */
  openedItemUid: string
  /** Show an item beside the list. The rest of the list goes with it, so that
   * stepping on from one goes to the next thing raised. */
  onOpenItem: (itemUid: string, siblingUids: string[]) => void
}

/**
 * What has been raised on the item being reviewed, as a list to settle.
 *
 * Raised while curating or by an import, on whatever item it is about, and
 * answered here because that is where the whole case is in front of you.
 * Settling one leaves it on record rather than removing it.
 */
export default function ReviewIssues({
  reviewUnitUid,
  openedItemUid,
  onOpenItem,
}: ReviewIssuesProps): ReactElement {
  const queryClient = useQueryClient()
  const issuesQuery = useQuery({
    queryKey: queryKeys.item.reviewIssues(reviewUnitUid),
    queryFn: async () => await itemApi.getReviewIssues(reviewUnitUid),
  })
  const resolveMutation = useMutation({
    mutationFn: async (issueUid: string) => await itemApi.resolveReviewIssue(issueUid),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.item.reviewIssues(reviewUnitUid),
      })
    },
  })

  if (issuesQuery.isLoading) {
    return <LinearProgress />
  }
  // Everything open on the unit, whoever raised it: this is what the case is
  // in the queue for, and it is the one place that answers that. What
  // validation raised is listed here as well as under what is not valid,
  // which stays as the live view of the items themselves.
  const issues = issuesQuery.data ?? []
  if (issues.length === 0) {
    return <Typography sx={{ p: 2 }}>Nothing is open here.</Typography>
  }
  return (
    <Box sx={{ height: '100%', overflowY: 'auto' }}>
      <List dense>
        {issues.map((issue) => (
          <ListItem
            key={issue.uid}
            divider
            // Nothing to offer for what validation raised: it is settled by
            // the item becoming valid or leaving the project, and settling it
            // by hand would take the case out of the queue with the item still
            // not valid — which is what reviewing the case is refused for.
            secondaryAction={
              issue.source === ReviewIssueSource.Validation ? (
                // The slot is kept and left empty rather than dropped: a row
                // without it is wider than the rows that carry a button, and
                // the highlight steps in and out as the list is read down.
                <Box sx={{ width: 30 }} />
              ) : (
                <Tooltip title="Settle">
                  <span>
                    <IconButton
                      size="small"
                      disabled={resolveMutation.isPending}
                      onClick={() => resolveMutation.mutate(issue.uid)}
                    >
                      <Check fontSize="small" />
                    </IconButton>
                  </span>
                </Tooltip>
              )
            }
          >
            <ListItemButton
              selected={issue.itemUid === openedItemUid}
              onClick={() =>
                onOpenItem(
                  issue.itemUid,
                  issues.map((other) => other.itemUid),
                )
              }
            >
              {/* What raised it, in a column of its own: which kind it is
                  decides what a reviewer does with it, and reading that off
                  the end of a wrapped sentence made it the easiest part of
                  the row to miss. */}
              <Chip
                size="small"
                variant="outlined"
                label={SOURCE_NAMES[issue.source]}
                sx={{ mr: 1, minWidth: 116, flexShrink: 0 }}
              />
              <ListItemText primary={issue.itemIdentifier} secondary={issue.reason} />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  )
}
