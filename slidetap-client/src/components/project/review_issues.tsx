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

/** What to call a source in the list, where it was not a person. */
const SOURCE_NAMES: Record<ReviewIssueSource, string> = {
  [ReviewIssueSource.User]: '',
  [ReviewIssueSource.MetadataImporter]: 'from the metadata import',
  [ReviewIssueSource.ImageImporter]: 'from the image import',
  [ReviewIssueSource.Validation]: 'not valid',
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
  // What validation raised is shown as what is not valid, in the tab that
  // lists exactly that and stays live rather than repeating it here. This tab
  // is what somebody asked to have looked at.
  const issues = (issuesQuery.data ?? []).filter(
    (issue) => issue.source !== ReviewIssueSource.Validation,
  )
  if (issues.length === 0) {
    return <Typography sx={{ p: 2 }}>Nobody has raised anything here.</Typography>
  }
  return (
    <Box sx={{ height: '100%', overflowY: 'auto' }}>
      <List dense>
        {issues.map((issue) => (
          <ListItem
            key={issue.uid}
            divider
            secondaryAction={
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
              <ListItemText
                primary={issue.itemIdentifier}
                secondary={
                  issue.source === ReviewIssueSource.User
                    ? issue.reason
                    : `${issue.reason} — ${SOURCE_NAMES[issue.source]}`
                }
              />
            </ListItemButton>
          </ListItem>
        ))}
      </List>
    </Box>
  )
}
