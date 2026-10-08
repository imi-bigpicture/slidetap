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
  Card,
  CardActions,
  CardContent,
  Chip,
  LinearProgress,
  List,
  ListItemButton,
  ListItemText,
  Stack,
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
import DisplayAttribute from 'src/components/attribute/display_attribute'
import { useProjectActions } from 'src/contexts/project_actions/project_actions_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import { SchemaContextProvider } from 'src/contexts/schema/schema_context_provider'
import { ItemDetailAction } from 'src/models/action'
import {
  newAttribute,
  type Attribute,
  type AttributeValueTypes,
} from 'src/models/attribute'
import {
  MigrationObjectKind,
  MigrationState,
  type MigrationAttributeIssue,
  type MigrationObject,
  type ProjectMigration,
} from 'src/models/migration'
import type { Project } from 'src/models/project'
import { ProjectStatus } from 'src/models/project_status'
import type { AttributeSchema } from 'src/models/schema/attribute_schema'
import { rootDisplayName, type RootSchema } from 'src/models/schema/root_schema'
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

/** Converting a project to the root of new projects, in steps.
 *
 * Started here, the conversion is planned on the server, and what it could not
 * convert is then decided attribute by attribute, item by item, before it is
 * submitted to be completed, or reverted. Nothing can be changed in the project
 * meanwhile. */
function Migrate({ project }: MigrateProps): ReactElement {
  const migrating = project.status === ProjectStatus.MIGRATING
  const migrationQuery = useQuery({
    queryKey: queryKeys.project.migration(project.uid),
    queryFn: async () => {
      return await projectApi.getMigration(project.uid)
    },
    enabled: migrating,
    // Planned and completed by tasks, which say when they are done by the
    // state.
    refetchInterval: (query) => {
      const state = query.state.data?.state
      return state === MigrationState.PLANNING || state === MigrationState.COMPLETING
        ? 2000
        : false
    },
  })
  if (!migrating) {
    return <StartMigration project={project} />
  }
  if (migrationQuery.isError) {
    return <Alert severity="error">{refusal(migrationQuery.error)}</Alert>
  }
  const migration = migrationQuery.data
  if (migration === undefined) {
    return <LinearProgress />
  }
  if (migration === null) {
    return <Alert severity="info">The project is being converted.</Alert>
  }
  return (
    <SchemaContextProvider rootSchemaUid={migration.targetRootSchemaUid}>
      <MigrationInProgress project={project} migration={migration} />
    </SchemaContextProvider>
  )
}

export default Migrate

/** Starting a conversion, where the project can be converted now. */
function StartMigration({ project }: MigrateProps): ReactElement {
  const queryClient = useQueryClient()
  const rootSchema = useSchemaContext()
  const [open, setOpen] = React.useState(false)
  const startMutation = useMutation({
    mutationFn: () => projectApi.createMigration(project.uid),
    onSuccess: (migration) => {
      queryClient.setQueryData(queryKeys.project.migration(project.uid), migration)
      void queryClient.invalidateQueries({
        queryKey: queryKeys.project.detail(project.uid),
      })
      setOpen(false)
    },
  })
  // Where the project cannot be converted now, why not is said.
  const { hasMigration, migrateRefusal } = useProjectActions()
  const canMigrate = hasMigration && migrateRefusal === null
  return (
    <Stack spacing={1}>
      <Typography>
        The project is on {rootDisplayName(rootSchema)}, which it can be converted from.
        The conversion is planned first: what it cannot convert by itself is then
        decided here, attribute by attribute, before it is completed. Nothing can be
        changed in the project until the conversion is completed or reverted.
      </Typography>
      {migrateRefusal !== null && (
        <Alert severity="info">
          The project cannot be converted: {migrateRefusal}.
        </Alert>
      )}
      <Stack direction="row">
        <Button
          disabled={!canMigrate || startMutation.isPending}
          onClick={() => setOpen(true)}
        >
          Convert
        </Button>
      </Stack>
      {startMutation.isError && (
        <Alert severity="error">{refusal(startMutation.error)}</Alert>
      )}
      <Dialog open={open} onClose={() => setOpen(false)}>
        <DialogTitle>Convert project?</DialogTitle>
        <DialogContent>
          <Typography>
            The project is locked until the conversion is completed or reverted.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            color="warning"
            variant="contained"
            disabled={startMutation.isPending}
            onClick={() => startMutation.mutate()}
          >
            Convert
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  )
}

/** A conversion under way, by its state, with the target root as the schema. */
function MigrationInProgress({
  project,
  migration,
}: {
  project: Project
  migration: ProjectMigration
}): ReactElement {
  const queryClient = useQueryClient()
  const migrationKey = queryKeys.project.migration(project.uid)
  const done = (): void => {
    void queryClient.invalidateQueries({ queryKey: migrationKey })
    void queryClient.invalidateQueries({
      queryKey: queryKeys.project.detail(project.uid),
    })
  }
  const revertMutation = useMutation({
    mutationFn: () => projectApi.revertMigration(project.uid),
    onSuccess: (updatedProject) => {
      queryClient.setQueryData(queryKeys.project.detail(project.uid), updatedProject)
      queryClient.setQueryData(migrationKey, null)
      done()
    },
  })
  const submitMutation = useMutation({
    mutationFn: () => projectApi.submitMigration(project.uid),
    onSuccess: (submitted) => {
      queryClient.setQueryData(migrationKey, submitted)
    },
  })
  const revertButton = (
    <Button
      color="warning"
      disabled={revertMutation.isPending}
      onClick={() => revertMutation.mutate()}
    >
      Revert
    </Button>
  )
  return (
    <Stack spacing={1}>
      <Typography>
        Converting to {migration.targetRootSchemaName}. Nothing can be changed in the
        project until the conversion is completed or reverted.
      </Typography>
      {migration.state === MigrationState.PLANNING && (
        <>
          <Typography>Planning the conversion.</Typography>
          <LinearProgress />
        </>
      )}
      {migration.state === MigrationState.COMPLETING && (
        <>
          <Typography>Completing the conversion.</Typography>
          <LinearProgress />
        </>
      )}
      {migration.state === MigrationState.FAILED && (
        <Alert severity="error">
          The conversion failed, and the project is as it was before it:{' '}
          {migration.error ?? 'why is in the log of the server'}. Revert it to set the
          project back.
        </Alert>
      )}
      {migration.state === MigrationState.CURATING && (
        <>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <Typography>
              {migration.decided} of {migration.attributeIssues} decided
            </Typography>
            <Button
              variant="contained"
              disabled={
                migration.decided < migration.attributeIssues ||
                submitMutation.isPending
              }
              onClick={() => submitMutation.mutate()}
            >
              Submit
            </Button>
            {revertButton}
          </Stack>
          {submitMutation.isError && (
            <Alert severity="error">{refusal(submitMutation.error)}</Alert>
          )}
          <CurateMigration project={project} migration={migration} />
        </>
      )}
      {(migration.state === MigrationState.PLANNING ||
        migration.state === MigrationState.FAILED) && (
        <Stack direction="row">{revertButton}</Stack>
      )}
      {revertMutation.isError && (
        <Alert severity="error">{refusal(revertMutation.error)}</Alert>
      )}
    </Stack>
  )
}

/** The objects with something to decide or dropped, and the selected one's. */
function CurateMigration({
  project,
  migration,
}: {
  project: Project
  migration: ProjectMigration
}): ReactElement {
  const [selectedUid, setSelectedUid] = React.useState<string | undefined>(
    migration.objects.find((object) =>
      object.attributeIssues.some((issue) => !issue.decided),
    )?.uid ?? migration.objects[0]?.uid,
  )
  const selected = migration.objects.find((object) => object.uid === selectedUid)
  if (migration.objects.length === 0) {
    return <Typography>Everything is converted: nothing is left to decide.</Typography>
  }
  return (
    <Grid container spacing={1}>
      <Grid size={{ xs: 3 }}>
        <List dense>
          {migration.objects.map((object) => {
            const decided = object.attributeIssues.filter(
              (issue) => issue.decided,
            ).length
            return (
              <ListItemButton
                key={object.uid}
                selected={object.uid === selectedUid}
                onClick={() => setSelectedUid(object.uid)}
              >
                <ListItemText
                  primary={object.identifier}
                  secondary={`${object.targetSchemaDisplayName}: ${decided} of ${object.attributeIssues.length} decided`}
                />
              </ListItemButton>
            )
          })}
        </List>
      </Grid>
      <Grid size={{ xs: 9 }}>
        {selected !== undefined && (
          <CurateObject key={selected.uid} project={project} object={selected} />
        )}
      </Grid>
    </Grid>
  )
}

/** The target attribute schema of an attribute issue of an object. */
function issueSchema(
  rootSchema: RootSchema,
  object: MigrationObject,
  issue: MigrationAttributeIssue,
): AttributeSchema | undefined {
  const schema =
    object.kind === MigrationObjectKind.PROJECT
      ? rootSchema.project
      : object.kind === MigrationObjectKind.DATASET
        ? rootSchema.dataset
        : {
            ...rootSchema.samples,
            ...rootSchema.images,
            ...rootSchema.observations,
            ...rootSchema.annotations,
          }[object.targetSchemaUid]
  return schema?.attributes[issue.tag] ?? schema?.privateAttributes[issue.tag]
}

function CurateObject({
  project,
  object,
}: {
  project: Project
  object: MigrationObject
}): ReactElement {
  const rootSchema = useSchemaContext()
  return (
    <Stack spacing={1}>
      <Typography variant="h6">
        {object.identifier} ({object.targetSchemaDisplayName})
      </Typography>
      {object.dropped.length > 0 && (
        <Alert severity="info">
          Dropped, with no counterpart:{' '}
          {object.dropped
            .map((dropped) => `${dropped.displayName} (${dropped.displayValue ?? ''})`)
            .join(', ')}
        </Alert>
      )}
      {object.attributeIssues.map((issue) => {
        const schema = issueSchema(rootSchema, object, issue)
        return schema === undefined ? (
          <Alert key={issue.uid} severity="error">
            {issue.tag} is not an attribute of {object.targetSchemaDisplayName}.
          </Alert>
        ) : (
          <CurateIssue
            key={issue.uid}
            project={project}
            issue={issue}
            schema={schema}
          />
        )
      })}
    </Stack>
  )
}

/** One attribute to decide: the original value, why it was not converted, and
 * the editor of the target attribute, starting from what is decided or else
 * what could be converted. */
function CurateIssue({
  project,
  issue,
  schema,
}: {
  project: Project
  issue: MigrationAttributeIssue
  schema: AttributeSchema
}): ReactElement {
  const queryClient = useQueryClient()
  const [draft, setDraft] = React.useState<Attribute<AttributeValueTypes>>(
    issue.decision ??
      issue.proposed ??
      newAttribute(schema.uid, schema.attributeValueType, null, ''),
  )
  const decideMutation = useMutation({
    mutationFn: (attribute: Attribute<AttributeValueTypes> | null) =>
      projectApi.decideMigrationAttributeIssue(project.uid, issue.uid, attribute),
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.project.migration(project.uid),
      })
    },
  })
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1}>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <Typography variant="subtitle1">{issue.displayName}</Typography>
            <Chip
              size="small"
              color={issue.decided ? 'success' : 'default'}
              label={
                !issue.decided ? 'Undecided' : issue.leftEmpty ? 'Left empty' : 'Set'
              }
            />
          </Stack>
          <Typography variant="body2">
            Was: {issue.original?.displayValue ?? '—'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {issue.reason}
          </Typography>
          <DisplayAttribute
            attribute={draft}
            schema={schema}
            action={ItemDetailAction.EDIT}
            handleAttributeUpdate={(_tag, attribute) => setDraft(attribute)}
            showValueControls={false}
          />
          {decideMutation.isError && (
            <Alert severity="error">{refusal(decideMutation.error)}</Alert>
          )}
        </Stack>
      </CardContent>
      <CardActions>
        <Button
          disabled={decideMutation.isPending}
          onClick={() => decideMutation.mutate(draft)}
        >
          Set value
        </Button>
        <Button
          disabled={decideMutation.isPending}
          onClick={() => decideMutation.mutate(null)}
        >
          Leave empty
        </Button>
      </CardActions>
    </Card>
  )
}
