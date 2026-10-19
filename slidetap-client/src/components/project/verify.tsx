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

import {
  Cancel,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Casino,
  HelpOutlined,
  RemoveCircleOutlined,
  Update,
} from '@mui/icons-material'
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
  LinearProgress,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Stack,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo, useState, type ReactElement } from 'react'
import { useDetailDock } from 'src/components/item/detail_dock'
import ItemViewHeader from 'src/components/item/item_view_header'
import ReviewPanels from 'src/components/project/review_panels'
import { tabLabel, tabsFor } from 'src/components/project/review_tabs'
import { suggestionReason } from 'src/components/project/verification_suggestion'
import SplitPanel from 'src/components/split_panel'
import {
  ProjectActionsContext,
  useProjectActions,
} from 'src/contexts/project_actions/project_actions_context'
import { usePseudonym } from 'src/contexts/pseudonym/pseudonym_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import type { Batch } from 'src/models/batch'
import { BatchStatus } from 'src/models/batch_status'
import type { Project } from 'src/models/project'
import { getDisplayIdentifier } from 'src/models/pseudonym'
import {
  VerificationState,
  VerificationStateStrings,
  VerificationVerdict,
  type VerificationEntry,
  type VerificationDecision,
  type VerificationSuggestion,
} from 'src/models/verification'
import { ApiError } from 'src/services/api/api_methods'
import batchApi from 'src/services/api/batch.api'
import { queryKeys } from 'src/services/query_keys'

/** Stands for no state filter in the select, which cannot hold undefined. */
const ALL_STATES = 'all'

/** As long as a reason can be: what fits in the issue it raises, after the
 * 21 characters the issue says before it. */
const MAX_REASON_LENGTH = 512 - 'Failed verification: '.length

/** The icon a queue row carries for where it stands, coloured by whether it
 * needs anything more. */
function stateIcon(state: VerificationState): ReactElement {
  switch (state) {
    case VerificationState.Passed:
      return (
        <CheckCircle fontSize="small" sx={{ color: 'success.main', opacity: 0.7 }} />
      )
    case VerificationState.Failed:
      return <Cancel fontSize="small" sx={{ color: 'error.main', opacity: 0.7 }} />
    case VerificationState.NeedsRecheck:
      return <Update fontSize="small" sx={{ color: 'warning.main', opacity: 0.7 }} />
    case VerificationState.Removed:
      return <RemoveCircleOutlined fontSize="small" sx={{ color: 'text.disabled' }} />
    default:
      return (
        <HelpOutlined fontSize="small" sx={{ color: 'text.secondary', opacity: 0.7 }} />
      )
  }
}

/** What to say about a draw or a decision that did not go through: what the
 * server said where it refused, and that it failed otherwise. Said beside
 * what was tried rather than thrown, since a mutation's error is not seen by
 * the error boundary. */
function failureOf(error: Error): string {
  if (error instanceof ApiError && (error.status === 409 || error.status === 400)) {
    return error.body ?? error.message
  }
  return `It failed: ${error.message}`
}

interface VerifyProps {
  project: Project
  batch?: Batch
}

/**
 * Verifies a batch: review units drawn from it at random, checked one at a
 * time, each passed or failed.
 *
 * Laid out as the review queue is, since it is the same work of being handed
 * a case and deciding on it; what differs is what put the case in front of
 * the verifier, which is a draw rather than something being wrong. A failed
 * case is raised for review with the reason, fixed where everything raised is
 * fixed, and comes back here to be passed again.
 *
 * Only offered where the schema of the project declares a verification
 * policy.
 */
export default function Verify({ project, batch }: VerifyProps): ReactElement {
  const rootSchema = useSchemaContext()
  const queryClient = useQueryClient()
  const { pseudonymMode } = usePseudonym()
  const projectActions = useProjectActions()
  const canEdit = projectActions.edit
  // The panels show the case as it is, and nothing in them changes it: what a
  // verifier finds wrong is failed with a reason and fixed in review, so that
  // the failure is counted rather than mended here unseen.
  const readOnlyActions = useMemo(
    () => ({ ...projectActions, edit: false }),
    [projectActions],
  )
  const [selectedUid, setSelectedUid] = useState<string>()
  const [tabIndex, setTabIndex] = useState(0)
  const [queueOpen, setQueueOpen] = useState(true)
  const [stateFilter, setStateFilter] = useState<VerificationState>()
  const [drawOpen, setDrawOpen] = useState(false)
  const [failOpen, setFailOpen] = useState(false)
  const [refusal, setRefusal] = useState<string>()
  const dock = useDetailDock(project.uid, batch?.uid)

  const verificationQuery = useQuery({
    queryKey: queryKeys.batch.verification(batch?.uid ?? ''),
    queryFn: async () => await batchApi.getVerification(batch?.uid ?? ''),
    enabled: batch !== undefined,
  })
  const verification = verificationQuery.data
  // Drawn and decided while the images are processed and the batch is not yet
  // completed, and looked through, not decided on, at any other time.
  const canDecide =
    canEdit && batch?.status === BatchStatus.IMAGE_POST_PROCESSING_COMPLETE

  const unitSchema = useMemo(() => {
    const uid = rootSchema.reviewUnit?.schemaUid
    if (uid === undefined) {
      return undefined
    }
    return (
      rootSchema.samples[uid] ??
      rootSchema.images[uid] ??
      rootSchema.observations[uid] ??
      rootSchema.annotations[uid]
    )
  }, [rootSchema])

  const queue = useMemo(
    () =>
      (verification?.entries ?? []).filter(
        (entry) => stateFilter === undefined || entry.state === stateFilter,
      ),
    [verification, stateFilter],
  )
  const index = queue.findIndex((entry) => entry.uid === selectedUid)
  const current: VerificationEntry | undefined = index === -1 ? queue[0] : queue[index]

  const tabs = tabsFor(
    rootSchema,
    unitSchema?.uid,
    rootSchema.reviewUnit?.verification?.layout ?? null,
  )
  const shownTabIndex = Math.min(tabIndex, Math.max(tabs.length - 1, 0))
  const tab = tabs[shownTabIndex]

  const canDecideCurrent =
    canDecide && current !== undefined && current.state !== VerificationState.Removed

  const [shownUid, setShownUid] = useState(current?.uid)
  if (current?.uid !== shownUid) {
    setShownUid(current?.uid)
    setRefusal(undefined)
  }

  const invalidate = useCallback((): void => {
    if (batch !== undefined) {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.batch.verification(batch.uid),
      })
    }
    // Failing raises an issue and flags the case, and passing settles it.
    void queryClient.invalidateQueries({ queryKey: queryKeys.item.all })
  }, [batch, queryClient])

  const decideMutation = useMutation({
    mutationFn: async ({
      entryUid,
      decision,
    }: {
      entryUid: string
      decision: VerificationDecision
    }) => await batchApi.decideVerification(entryUid, decision),
    onSuccess: () => {
      setRefusal(undefined)
      // Stepped on before the list moves under it, as in review: a decided
      // case leaves a queue filtered to what is pending.
      if (stateFilter !== undefined) {
        const position = index === -1 ? 0 : index
        setSelectedUid(queue[position + 1]?.uid ?? queue[position - 1]?.uid)
      }
      invalidate()
    },
    onError: (error) => {
      setRefusal(failureOf(error))
      invalidate()
    },
  })

  const step = useCallback(
    (offset: number) => {
      const next = queue[(index === -1 ? 0 : index) + offset]
      if (next !== undefined) {
        setSelectedUid(next.uid)
      }
    },
    [queue, index],
  )

  // As in review: Ctrl+, and Ctrl+. step, Ctrl+Enter passes the case. Failing
  // asks why, so it has no key of its own.
  const { mutate: decide, isPending: decidePending } = decideMutation
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (!event.ctrlKey || failOpen || drawOpen) {
        return
      }
      if (event.key === ',') {
        event.preventDefault()
        step(-1)
      } else if (event.key === '.') {
        event.preventDefault()
        step(1)
      } else if (
        event.key === 'Enter' &&
        current !== undefined &&
        canDecideCurrent &&
        !decidePending
      ) {
        event.preventDefault()
        decide({
          entryUid: current.uid,
          decision: { verdict: VerificationVerdict.Passed },
        })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [step, current, decide, decidePending, canDecideCurrent, failOpen, drawOpen])

  if (batch === undefined) {
    return <Typography sx={{ p: 2 }}>Pick a batch to verify.</Typography>
  }
  if (verification === undefined) {
    return <LinearProgress />
  }
  if (!verification.verified) {
    return (
      <Typography sx={{ p: 2 }}>
        The schema of this project does not verify batches.
      </Typography>
    )
  }

  const decided = verification.entries.filter(
    (entry) => entry.decidedAt !== null,
  ).length
  const standing = `${decided} of ${verification.entries.length} decided`

  return (
    <Box
      sx={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 80px)' }}
    >
      {verification.blocking.length > 0 && (
        <Alert severity="warning" sx={{ mb: 1, py: 0 }}>
          The batch cannot be locked yet.
          {verification.blocking.map((reason) => (
            <Box key={reason}>{reason}</Box>
          ))}
        </Alert>
      )}
      {/* Counted by what was found, fixed since or not: a case found wrong
          says the cases not drawn may be wrong as well, which fixing it does
          not change. Drawing another round is what answers it, so only the
          latest round warns. */}
      {verification.rounds
        .filter(
          (verificationRound) =>
            verificationRound.failureRateExceeded &&
            verificationRound.number === verification.rounds.length,
        )
        .map((verificationRound) => (
          <Alert key={verificationRound.uid} severity="warning" sx={{ mb: 1, py: 0 }}>
            Round {verificationRound.number}: {verificationRound.failed} of{' '}
            {verificationRound.decided} checked{' '}
            {verificationRound.failed === 1 ? 'was' : 'were'} found wrong, more than the
            project expects. Fixing them does not change that: the cases not drawn may
            have the same problems. Consider drawing more.
          </Alert>
        ))}
      <Box sx={{ display: 'flex', flexGrow: 1, minHeight: 0, gap: 1 }}>
        <Box
          sx={{
            width: queueOpen ? 240 : 40,
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            borderRight: 1,
            borderColor: 'divider',
          }}
        >
          <Stack
            direction="row"
            sx={{
              alignItems: 'center',
              ...(queueOpen ? { pl: 1 } : { justifyContent: 'center' }),
            }}
          >
            {queueOpen && (
              <>
                <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
                  {standing}
                </Typography>
                <Tooltip
                  title={
                    verification.undrawn === 0
                      ? 'Every unit has been drawn'
                      : `Draw units to verify (${verification.undrawn} not drawn yet)`
                  }
                >
                  <span>
                    <IconButton
                      size="small"
                      disabled={!canDecide || verification.undrawn === 0}
                      onClick={() => setDrawOpen(true)}
                    >
                      <Casino />
                    </IconButton>
                  </span>
                </Tooltip>
              </>
            )}
            <IconButton size="small" onClick={() => setQueueOpen(!queueOpen)}>
              {queueOpen ? <ChevronLeft /> : <ChevronRight />}
            </IconButton>
          </Stack>
          {queueOpen && (
            <>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ px: 1, mb: 1 }}
              >
                {verification.rounds.length === 0
                  ? `Nothing drawn yet from ${verification.populationSize} units.`
                  : verification.rounds
                      .map(
                        (verificationRound) =>
                          `Round ${verificationRound.number}: ${verificationRound.drawn} of ${verificationRound.populationSize}, ${verificationRound.failed} failed`,
                      )
                      .join(' · ')}
              </Typography>
              <TextField
                select
                size="small"
                value={stateFilter ?? ALL_STATES}
                onChange={(event) =>
                  setStateFilter(
                    event.target.value === ALL_STATES
                      ? undefined
                      : (event.target.value as VerificationState),
                  )
                }
                sx={{ mx: 1, mb: 1 }}
              >
                <MenuItem value={ALL_STATES}>All</MenuItem>
                {Object.values(VerificationState).map((state) => (
                  <MenuItem key={state} value={state}>
                    {VerificationStateStrings[state]}
                  </MenuItem>
                ))}
              </TextField>
              <List dense sx={{ overflowY: 'auto', flexGrow: 1 }}>
                {queue.map((entry) => (
                  <Tooltip
                    key={entry.uid}
                    title={entry.reason ?? VerificationStateStrings[entry.state]}
                    placement="right"
                  >
                    <ListItemButton
                      selected={entry.uid === current?.uid}
                      onClick={() => setSelectedUid(entry.uid)}
                    >
                      <ListItemText
                        primary={getDisplayIdentifier(
                          {
                            uid: entry.unitUid,
                            identifier: entry.identifier,
                            pseudonym: entry.pseudonym,
                          },
                          pseudonymMode,
                        )}
                        secondary={[
                          verification.rounds.length > 1
                            ? `Round ${entry.roundNumber}`
                            : undefined,
                          VerificationStateStrings[entry.state],
                        ]
                          .filter((part) => part !== undefined)
                          .join(' · ')}
                        slotProps={{
                          primary: { noWrap: true },
                          secondary: { noWrap: true, variant: 'caption' },
                        }}
                      />
                      {stateIcon(entry.state)}
                    </ListItemButton>
                  </Tooltip>
                ))}
              </List>
            </>
          )}
        </Box>
        <Box
          sx={{ flexGrow: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}
        >
          {current === undefined ? (
            <Typography sx={{ p: 2 }}>
              {verification.entries.length === 0
                ? 'Nothing has been drawn to verify yet.'
                : 'Nothing here.'}
            </Typography>
          ) : (
            <>
              <ItemViewHeader
                flat
                identifier={getDisplayIdentifier(
                  {
                    uid: current.unitUid,
                    identifier: current.identifier,
                    pseudonym: current.pseudonym,
                  },
                  pseudonymMode,
                )}
                onPrevious={() => step(-1)}
                onNext={() => step(1)}
                hasPrevious={index > 0}
                hasNext={index !== -1 && index < queue.length - 1}
              >
                <Typography variant="body2" color="text.secondary" sx={{ mx: 1 }}>
                  {VerificationStateStrings[current.state]}
                </Typography>
                <Tooltip title="Pass (Ctrl+Enter)">
                  <span>
                    <IconButton
                      size="small"
                      disabled={!canDecideCurrent || decideMutation.isPending}
                      onClick={() =>
                        decideMutation.mutate({
                          entryUid: current.uid,
                          decision: { verdict: VerificationVerdict.Passed },
                        })
                      }
                    >
                      <CheckCircle sx={{ color: 'success.main', opacity: 0.7 }} />
                    </IconButton>
                  </span>
                </Tooltip>
                <Tooltip title="Fail, with why">
                  <span>
                    <IconButton
                      size="small"
                      disabled={!canDecideCurrent || decideMutation.isPending}
                      onClick={() => setFailOpen(true)}
                    >
                      <Cancel sx={{ color: 'error.main', opacity: 0.7 }} />
                    </IconButton>
                  </span>
                </Tooltip>
              </ItemViewHeader>
              {refusal !== undefined && (
                <Alert
                  severity="error"
                  onClose={() => setRefusal(undefined)}
                  sx={{ mx: 1, mb: 1, py: 0 }}
                >
                  {refusal}
                </Alert>
              )}
              {current.reason !== null && (
                <Alert
                  severity={
                    current.verdict === VerificationVerdict.Failed ? 'error' : 'info'
                  }
                  sx={{ mx: 1, mb: 1, py: 0 }}
                >
                  {current.verdict === VerificationVerdict.Failed
                    ? `Failed: ${current.reason}`
                    : `Passed after failing: ${current.reason}`}
                </Alert>
              )}
              <Tabs
                value={shownTabIndex}
                onChange={(_, value: number) => setTabIndex(value)}
                variant="scrollable"
                sx={{ minHeight: 36, '& .MuiTab-root': { minHeight: 36 } }}
              >
                {tabs.map((each, tabPosition) => (
                  <Tab key={tabPosition} label={tabLabel(each)} />
                ))}
              </Tabs>
              <Divider />
              <Box sx={{ flexGrow: 1, minHeight: 0, pt: 1 }}>
                <ProjectActionsContext.Provider value={readOnlyActions}>
                  <SplitPanel fillHeight panel={dock.panel}>
                    <Box sx={{ height: '100%', minHeight: 0, display: 'flex', gap: 1 }}>
                      <ReviewPanels
                        projectUid={project.uid}
                        batchUid={batch.uid}
                        itemUid={current.unitUid}
                        tab={tab}
                        displayName={`verifying ${unitSchema?.displayName ?? 'this'}`}
                        openedItemUid={dock.openedUid}
                        onOpenItem={dock.open}
                      />
                    </Box>
                  </SplitPanel>
                </ProjectActionsContext.Provider>
              </Box>
            </>
          )}
        </Box>
      </Box>
      {/* Mounted only while open, so that what it offers is read once as it
          opens rather than written over by a refetch while it is being
          filled in. */}
      {drawOpen && (
        <DrawDialog
          suggestion={verification.suggestion}
          undrawn={verification.undrawn}
          required={verification.required}
          batchUid={batch.uid}
          onClose={() => setDrawOpen(false)}
          onDrawn={() => {
            setDrawOpen(false)
            setStateFilter(undefined)
            invalidate()
          }}
        />
      )}
      {current !== undefined && (
        <FailDialog
          key={current.uid}
          open={failOpen}
          previousReason={current.reason}
          onClose={() => setFailOpen(false)}
          onFail={(reason) => {
            setFailOpen(false)
            decideMutation.mutate({
              entryUid: current.uid,
              decision: { verdict: VerificationVerdict.Failed, reason },
            })
          }}
        />
      )}
    </Box>
  )
}

interface DrawDialogProps {
  /** What the policy suggests drawing and why, read as the dialog opens. */
  suggestion: VerificationSuggestion | null
  undrawn: number
  /** Whether the policy requires a draw before the batch can be locked. */
  required: boolean
  batchUid: string
  onClose: () => void
  onDrawn: () => void
}

/** Asks how many to draw, offering what the policy suggests and saying why.
 * The seed is picked by the server, so that a draw cannot be steered. */
function DrawDialog({
  suggestion,
  undrawn,
  required,
  batchUid,
  onClose,
  onDrawn,
}: DrawDialogProps): ReactElement {
  const [size, setSize] = useState(String(suggestion?.size ?? 1))
  const [refusal, setRefusal] = useState<string>()
  const drawMutation = useMutation({
    mutationFn: async () =>
      await batchApi.drawVerificationRound(batchUid, { size: Number(size) }),
    onSuccess: onDrawn,
    onError: (error) => setRefusal(failureOf(error)),
  })
  const sizeValid = Number.isInteger(Number(size)) && Number(size) >= 1
  const minimum = suggestion?.minimumSize ?? 1
  return (
    <Dialog open onClose={onClose}>
      <DialogTitle>Draw units to verify</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Drawn at random from the {undrawn} units in the batch that have not been
            drawn yet.
          </Typography>
          {suggestion !== null && (
            <Typography variant="body2">{suggestionReason(suggestion)}</Typography>
          )}
          {required && (
            <Typography variant="body2" color="text.secondary">
              To lock the batch, at least {minimum} unit{minimum === 1 ? '' : 's'} must
              be drawn and decided, and none may stay failed. The rest of the suggestion
              is advice.
            </Typography>
          )}
          <TextField
            label="How many"
            type="number"
            value={size}
            error={!sizeValid}
            onChange={(event) => setSize(event.target.value)}
            slotProps={{ htmlInput: { min: 1, max: undrawn } }}
          />
          {refusal !== undefined && <Alert severity="error">{refusal}</Alert>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          disabled={!sizeValid || drawMutation.isPending}
          onClick={() => drawMutation.mutate()}
        >
          Draw
        </Button>
      </DialogActions>
    </Dialog>
  )
}

interface FailDialogProps {
  open: boolean
  previousReason: string | null
  onClose: () => void
  onFail: (reason: string) => void
}

/** Asks why a unit fails: the reason is what is raised for review, and what
 * whoever fixes it goes by. */
function FailDialog({
  open,
  previousReason,
  onClose,
  onFail,
}: FailDialogProps): ReactElement {
  const [reason, setReason] = useState(previousReason ?? '')
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Fail verification</DialogTitle>
      <DialogContent>
        <TextField
          autoFocus
          fullWidth
          multiline
          minRows={2}
          label="What is wrong"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          slotProps={{ htmlInput: { maxLength: MAX_REASON_LENGTH } }}
          sx={{ mt: 1 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          color="error"
          disabled={reason.trim() === ''}
          onClick={() => onFail(reason.trim())}
        >
          Fail
        </Button>
      </DialogActions>
    </Dialog>
  )
}
