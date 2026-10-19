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
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseMutationResult,
} from '@tanstack/react-query'
import React, { type ReactElement } from 'react'
import DisplayAttribute from 'src/components/attribute/display_attribute'
import { useProjectActions } from 'src/contexts/project_actions/project_actions_context'
import { useSchemaContext } from 'src/contexts/schema/schema_context'
import {
  progressPercent,
  progressText,
} from 'src/components/project/conversion_progress'
import { SchemaContextProvider } from 'src/contexts/schema/schema_context_provider'
import { ItemDetailAction } from 'src/models/action'
import {
  newAttribute,
  type Attribute,
  type AttributeValueTypes,
} from 'src/models/attribute'
import {
  MigrationStatus,
  type AttributeMigrationIssue,
  type EntityMigrationIssues,
  type MigrationProgress,
  type ProjectMigration,
} from 'src/models/migration'
import type { Project } from 'src/models/project'
import { ProjectStatus } from 'src/models/project_status'
import type { AttributeSchema } from 'src/models/schema/attribute_schema'
import type { ProjectSchema } from 'src/models/schema/project_schema'
import { rootDisplayName, type RootSchema } from 'src/models/schema/root_schema'
import { ApiError } from 'src/services/api/api_methods'
import projectApi from 'src/services/api/project_api'
import schemaApi from 'src/services/api/schema_api'
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
 * convert is then resolved attribute by attribute, item by item, before it is
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
    // status.
    refetchInterval: (query) => {
      const status = query.state.data?.status
      return status === MigrationStatus.PLANNING ||
        status === MigrationStatus.COMPLETING
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
    // Its error is shown beside the action.
    meta: { handlesError: true },
    onSuccess: (migration) => {
      queryClient.setQueryData(queryKeys.project.migration(project.uid), migration)
      void queryClient.invalidateQueries({
        queryKey: queryKeys.project.detail(project.uid),
      })
      setOpen(false)
    },
  })
  // Where the project cannot be converted now, why not is said.
  const { migrationAvailable, migrateRefusal } = useProjectActions()
  const canMigrate = migrationAvailable && migrateRefusal === null
  return (
    <Stack spacing={1}>
      <Typography>
        The project is on {rootDisplayName(rootSchema)}, which it can be converted from.
        The conversion is planned first: what it cannot convert by itself is then
        resolved here, attribute by attribute, before it is completed. Nothing can be
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

/** A conversion under way, by its status, with the target root as the schema. */
function MigrationInProgress({
  project,
  migration,
}: {
  project: Project
  migration: ProjectMigration
}): ReactElement {
  const queryClient = useQueryClient()
  const targetRoot = useSchemaContext()
  const migrationKey = queryKeys.project.migration(project.uid)
  const done = (): void => {
    void queryClient.invalidateQueries({ queryKey: migrationKey })
    void queryClient.invalidateQueries({
      queryKey: queryKeys.project.detail(project.uid),
    })
  }
  const revertMutation = useMutation({
    mutationFn: () => projectApi.revertMigration(project.uid),
    meta: { handlesError: true },
    onSuccess: (updatedProject) => {
      queryClient.setQueryData(queryKeys.project.detail(project.uid), updatedProject)
      queryClient.setQueryData(migrationKey, null)
      done()
    },
  })
  const submitMutation = useMutation({
    mutationFn: () => projectApi.submitMigration(project.uid),
    meta: { handlesError: true },
    onSuccess: (submitted) => {
      queryClient.setQueryData(migrationKey, submitted)
    },
  })
  const issues = migration.issues.flatMap((entity) => entity.attributeIssues)
  const resolvedCount = issues.filter((issue) => issue.resolvedAt !== null).length
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
        Converting to {rootDisplayName(targetRoot)}. Nothing can be changed in the
        project until the conversion is completed or reverted.
      </Typography>
      {migration.status === MigrationStatus.PLANNING && (
        <ConversionProgress
          title="Planning the conversion"
          progress={migration.progress}
          completing={false}
        />
      )}
      {migration.status === MigrationStatus.COMPLETING && (
        <ConversionProgress
          title="Completing the conversion"
          progress={migration.progress}
          completing={true}
        />
      )}
      {migration.status === MigrationStatus.FAILED && (
        <Alert severity="error">
          The conversion failed, and the project is as it was before it:{' '}
          {migration.error ?? 'why is in the log of the server'}. Revert it to set the
          project back.
        </Alert>
      )}
      {migration.status === MigrationStatus.CURATING && (
        <>
          <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
            <Typography>
              {resolvedCount} of {issues.length} resolved
            </Typography>
            <Button
              variant="contained"
              disabled={
                !issues.every((issue) => issue.resolvedAt !== null) ||
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
      {(migration.status === MigrationStatus.PLANNING ||
        migration.status === MigrationStatus.FAILED) && (
        <Stack direction="row">{revertButton}</Stack>
      )}
      {revertMutation.isError && (
        <Alert severity="error">{refusal(revertMutation.error)}</Alert>
      )}
    </Stack>
  )
}

/** How far planning or completing a conversion has come: the step it is on
 * and how many of its entities are done, or a running bar until it has
 * started. */
function ConversionProgress({
  title,
  progress,
  completing,
}: {
  title: string
  progress: MigrationProgress | null
  completing: boolean
}): ReactElement {
  const percent = progressPercent(progress)
  return (
    <>
      <Typography>{progressText(title, progress, completing)}</Typography>
      {percent === null ? (
        <LinearProgress />
      ) : (
        <LinearProgress variant="determinate" value={percent} />
      )}
    </>
  )
}

/** The entities with something to resolve or accept, and the selected one's. */
function CurateMigration({
  project,
  migration,
}: {
  project: Project
  migration: ProjectMigration
}): ReactElement {
  const [selectedUid, setSelectedUid] = React.useState<string | undefined>(
    migration.issues.find((entity) =>
      entity.attributeIssues.some((issue) => issue.resolvedAt === null),
    )?.uid ?? migration.issues[0]?.uid,
  )
  const selected = migration.issues.find((entity) => entity.uid === selectedUid)
  const targetRoot = useSchemaContext()
  // The schemas of dropped attributes are in the root the project is on.
  const sourceRootQuery = useQuery({
    queryKey: queryKeys.schema.root(migration.sourceRootSchemaUid),
    queryFn: async () => {
      return await schemaApi.getRootSchema(migration.sourceRootSchemaUid)
    },
  })
  if (sourceRootQuery.isError) {
    return <Alert severity="error">{refusal(sourceRootQuery.error)}</Alert>
  }
  if (sourceRootQuery.data === undefined) {
    return <LinearProgress />
  }
  if (migration.issues.length === 0) {
    return <Typography>Everything is converted: nothing is left to resolve.</Typography>
  }
  return (
    <Grid container spacing={1}>
      <Grid size={{ xs: 3 }}>
        <List dense>
          {migration.issues.map((entity) => {
            const resolved = entity.attributeIssues.filter(
              (issue) => issue.resolvedAt !== null,
            ).length
            return (
              <ListItemButton
                key={entity.uid}
                selected={entity.uid === selectedUid}
                onClick={() => setSelectedUid(entity.uid)}
              >
                <ListItemText
                  primary={entity.identifier}
                  secondary={`${entitySchema(targetRoot, entity.targetSchemaUid)?.displayName ?? ''}: ${resolved} of ${entity.attributeIssues.length} resolved`}
                />
              </ListItemButton>
            )
          })}
        </List>
      </Grid>
      <Grid size={{ xs: 9 }}>
        {selected !== undefined && (
          <CurateEntity
            key={selected.uid}
            project={project}
            entity={selected}
            sourceRoot={sourceRootQuery.data}
          />
        )}
      </Grid>
    </Grid>
  )
}

/** A project, dataset, or item schema, as far as an attribute issue needs it. */
type EntitySchema = Pick<
  ProjectSchema,
  'uid' | 'displayName' | 'attributes' | 'privateAttributes'
>

/** The project, dataset, and item schemas of a root. */
function entitySchemas(root: RootSchema): EntitySchema[] {
  return [
    root.project,
    root.dataset,
    ...Object.values(root.samples),
    ...Object.values(root.images),
    ...Object.values(root.observations),
    ...Object.values(root.annotations),
  ]
}

/** Find the project, dataset, or item schema of a uid in a root. */
function entitySchema(root: RootSchema, uid: string): EntitySchema | undefined {
  return entitySchemas(root).find((schema) => schema.uid === uid)
}

/** Find the top-level attribute schema of a uid in an entity schema. */
function attributeSchema(
  schema: EntitySchema | undefined,
  uid: string | undefined,
): AttributeSchema | undefined {
  if (schema === undefined) {
    return undefined
  }
  return [
    ...Object.values(schema.attributes),
    ...Object.values(schema.privateAttributes),
  ].find((attribute) => attribute.uid === uid)
}

function CurateEntity({
  project,
  entity,
  sourceRoot,
}: {
  project: Project
  entity: EntityMigrationIssues
  sourceRoot: RootSchema
}): ReactElement {
  const targetSchema = entitySchema(useSchemaContext(), entity.targetSchemaUid)
  return (
    <Stack spacing={1}>
      <Typography variant="h6">
        {entity.identifier} ({targetSchema?.displayName})
      </Typography>
      {entity.attributeIssues.map((issue) => {
        if (issue.targetAttributeSchemaUid === null) {
          const sourceUid = issue.original?.schemaUid
          const source = entitySchemas(sourceRoot)
            .map((schema) => attributeSchema(schema, sourceUid))
            .find((schema) => schema !== undefined)
          return (
            <AcceptDropped
              key={issue.uid}
              project={project}
              issue={issue}
              displayName={source?.displayName ?? sourceUid ?? ''}
            />
          )
        }
        const schema = attributeSchema(targetSchema, issue.targetAttributeSchemaUid)
        return schema === undefined ? (
          <Alert key={issue.uid} severity="error">
            Attribute schema {issue.targetAttributeSchemaUid} is not an attribute of{' '}
            {targetSchema?.displayName ?? entity.targetSchemaUid}.
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

/** Resolving an attribute issue, refreshing the migration when it is. */
function useResolveIssue(
  project: Project,
  issue: AttributeMigrationIssue,
): UseMutationResult<
  AttributeMigrationIssue,
  Error,
  Attribute<AttributeValueTypes> | null
> {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (attribute: Attribute<AttributeValueTypes> | null) =>
      projectApi.resolveMigrationAttributeIssue(project.uid, issue.uid, attribute),
    // Its error is shown beside the issue.
    meta: { handlesError: true },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: queryKeys.project.migration(project.uid),
      })
    },
  })
}

/** The name, status, original value, and problem of an attribute issue. */
function IssueHeader({
  issue,
  displayName,
  status,
}: {
  issue: AttributeMigrationIssue
  displayName: string
  status: string
}): ReactElement {
  return (
    <>
      <Stack direction="row" spacing={1} sx={{ alignItems: 'center' }}>
        <Typography variant="subtitle1">{displayName}</Typography>
        <Chip
          size="small"
          color={issue.resolvedAt !== null ? 'success' : 'default'}
          label={status}
        />
      </Stack>
      <Typography variant="body2">
        Was: {issue.original?.displayValue ?? '—'}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {issue.problem}
      </Typography>
    </>
  )
}

/** An attribute the conversion drops, which can only be accepted. */
function AcceptDropped({
  project,
  issue,
  displayName,
}: {
  project: Project
  issue: AttributeMigrationIssue
  displayName: string
}): ReactElement {
  const resolveMutation = useResolveIssue(project, issue)
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1}>
          <IssueHeader
            issue={issue}
            displayName={displayName}
            status={issue.resolvedAt === null ? 'Dropped' : 'Accepted'}
          />
          {resolveMutation.isError && (
            <Alert severity="error">{refusal(resolveMutation.error)}</Alert>
          )}
        </Stack>
      </CardContent>
      <CardActions>
        <Button
          disabled={resolveMutation.isPending || issue.resolvedAt !== null}
          onClick={() => resolveMutation.mutate(null)}
        >
          Accept
        </Button>
      </CardActions>
    </Card>
  )
}

/** One attribute to resolve: the original value, why it was not converted, and
 * the editor of the target attribute, starting from what is resolved or else
 * what could be converted. */
function CurateIssue({
  project,
  issue,
  schema,
}: {
  project: Project
  issue: AttributeMigrationIssue
  schema: AttributeSchema
}): ReactElement {
  const [draft, setDraft] = React.useState<Attribute<AttributeValueTypes>>(
    issue.resolved ??
      issue.proposed ??
      newAttribute(schema.uid, schema.attributeValueType, null, ''),
  )
  const resolveMutation = useResolveIssue(project, issue)
  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1}>
          <IssueHeader
            issue={issue}
            displayName={schema.displayName}
            status={
              issue.resolvedAt === null
                ? 'Unresolved'
                : issue.resolved === null
                  ? 'Left empty'
                  : 'Set'
            }
          />
          <DisplayAttribute
            attribute={draft}
            schema={schema}
            action={ItemDetailAction.EDIT}
            handleAttributeUpdate={(_tag, attribute) => setDraft(attribute)}
            showValueControls={false}
          />
          {resolveMutation.isError && (
            <Alert severity="error">{refusal(resolveMutation.error)}</Alert>
          )}
        </Stack>
      </CardContent>
      <CardActions>
        <Button
          disabled={resolveMutation.isPending}
          onClick={() => resolveMutation.mutate(draft)}
        >
          Set value
        </Button>
        <Button
          disabled={resolveMutation.isPending}
          onClick={() => resolveMutation.mutate(null)}
        >
          Leave empty
        </Button>
      </CardActions>
    </Card>
  )
}
