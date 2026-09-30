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
  Alert,
  LinearProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import Button from '@mui/material/Button'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import Grid from '@mui/material/Grid'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import { useProjectActions } from 'src/contexts/project_actions/project_actions_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import type { MigrationReport } from 'src/models/migration'
import type { Project } from 'src/models/project'
import { ProjectStatus } from 'src/models/project_status'
import { rootDisplayName } from 'src/models/schema/root_schema'
import { ApiError } from 'src/services/api/api_methods'
import projectApi from 'src/services/api/project_api'
import { queryKeys } from 'src/services/query_keys'

interface MigrateProps {
  project: Project
}

/** What the server said it would not do, rather than that something failed. */
function refusal(error: Error | null): string | undefined {
  if (error === null) {
    return undefined
  }
  return error instanceof ApiError ? (error.body ?? error.message) : error.message
}

/** Migrating a project to another root schema of its family, shown as
 * converting it.
 *
 * What the migration would do is worked out by migrating the project and
 * rolling it back, and shown before it is confirmed: what the curator will
 * have to fill in again is what was dropped, and what is invalid after. */
function Migrate({ project }: MigrateProps): ReactElement {
  const queryClient = useQueryClient()
  const rootSchema = useSchemaContext()
  const [open, setOpen] = React.useState(false)
  // The root a conversion started here was from, until the project is no
  // longer converting: a failed one sets it back to what it was, on that root.
  const [convertingFrom, setConvertingFrom] = React.useState<string | null>(null)
  const [failed, setFailed] = React.useState(false)
  const reportQuery = useQuery({
    queryKey: queryKeys.project.migration(project.uid),
    queryFn: async () => {
      return await projectApi.getMigration(project.uid)
    },
    enabled: open,
    // Worked out from the project as it is when the dialog is opened.
    staleTime: 0,
  })
  const migrateMutation = useMutation({
    mutationFn: (projectUid: string) => {
      return projectApi.migrate(projectUid)
    },
    onSuccess: (updatedProject) => {
      queryClient.setQueryData(queryKeys.project.detail(project.uid), updatedProject)
      setConvertingFrom(project.rootSchemaUid)
      setFailed(false)
      // Migrating offers nothing while it is under way.
      void queryClient.invalidateQueries({
        queryKey: queryKeys.project.actions(project.uid),
      })
      setOpen(false)
    },
  })
  const migrating = project.status === ProjectStatus.MIGRATING
  React.useEffect(() => {
    if (convertingFrom === null || migrating) {
      return
    }
    setFailed(project.rootSchemaUid === convertingFrom)
    setConvertingFrom(null)
  }, [convertingFrom, migrating, project.rootSchemaUid])
  // Offered only while a migration exists for the root the project is on,
  // which a finished conversion has moved it from, and the project can be
  // moved now: where it cannot, why not is said.
  const { migrate: canMigrate, migrateRefusal } = useProjectActions()
  return (
    <Grid
      container
      spacing={1}
      sx={{ justifyContent: 'flex-start', alignItems: 'flex-start' }}
    >
      <Grid size={{ xs: 12 }}>
        <Stack spacing={1}>
          <Typography>
            The project is on {rootDisplayName(rootSchema)}, which it can be converted
            from. Converting moves every item to the new schema, and the project is then
            in progress again for what the conversion dropped or left invalid to be
            filled in. Nothing can be changed in the project while it is converted.
          </Typography>
          {migrating && <LinearProgress />}
          {!migrating && migrateRefusal !== null && (
            <Alert severity="info">The project cannot be converted: {migrateRefusal}.</Alert>
          )}
          <Stack direction="row">
            <Button
              disabled={!canMigrate || migrating || migrateMutation.isPending}
              onClick={() => setOpen(true)}
            >
              Convert
            </Button>
          </Stack>
          {migrateMutation.isError && (
            <Alert severity="error">{refusal(migrateMutation.error)}</Alert>
          )}
          {failed && (
            <Alert severity="error">
              The conversion failed, and the project is as it was before it. Why is in
              the log of the server.
            </Alert>
          )}
        </Stack>
      </Grid>
      <Dialog open={open} onClose={() => setOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Convert project?</DialogTitle>
        <DialogContent>
          {reportQuery.isFetching && <LinearProgress />}
          {reportQuery.isError && (
            <Alert severity="error">{refusal(reportQuery.error)}</Alert>
          )}
          {reportQuery.data !== undefined && (
            <MigrationReportTable
              report={reportQuery.data}
              source={rootDisplayName(rootSchema)}
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            color="warning"
            variant="contained"
            // Not on a report the project may since have changed from.
            disabled={
              reportQuery.data === undefined ||
              reportQuery.isFetching ||
              migrateMutation.isPending
            }
            onClick={() => migrateMutation.mutate(project.uid)}
          >
            Convert
          </Button>
        </DialogActions>
      </Dialog>
    </Grid>
  )
}

export default Migrate

function MigrationReportTable({
  report,
  source,
}: {
  report: MigrationReport
  source: string
}): ReactElement {
  return (
    <Stack spacing={1}>
      <Typography>
        {report.items} items will be converted from {source} to{' '}
        {report.targetRootSchemaName}.
      </Typography>
      {report.attributes.length === 0 ? (
        <Typography>No attribute is dropped, and none is invalid after.</Typography>
      ) : (
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Attribute</TableCell>
              <TableCell align="right">Dropped</TableCell>
              <TableCell align="right">Invalid after</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {report.attributes.map((change) => (
              <TableRow key={`${change.attributeSchemaUid}-${change.tag}`}>
                <TableCell>{change.displayName}</TableCell>
                <TableCell align="right">{change.dropped}</TableCell>
                <TableCell align="right">{change.invalid}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </Stack>
  )
}
