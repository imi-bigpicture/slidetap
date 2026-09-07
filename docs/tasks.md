---
title: Tasks
layout: home
nav_order: 5
---

## Background tasks

Importing and exporting images and metadata runs in the background so that the
web application can keep answering requests while the work is in progress.
Tasks are [Procrastinate](https://procrastinate.readthedocs.io/) jobs. The queue
lives in the same Postgres database as the rest of the application, given by
`SLIDETAP_DBURI`, so no separate message broker is needed.

The tasks themselves ship with SlideTap and are defined in
[`task/tasks.py`](https://github.com/imi-bigpicture/slidetap/blob/main/slidetap-app/src/slidetap/task/tasks.py).
You do not write tasks. Each task calls into the
[site](site_implementations.md) and [dataset](dataset_implementations.md)
interfaces you implement, so your code runs inside a worker without knowing
about the queue.

| Task | Calls into |
|---|---|
| `download_and_pre_process_image` | `ImageImportInterface`, `MetadataImportInterface` |
| `post_process_image` | `ImageExportInterface` |
| `store_batch_images_to_outbox` | `ImageExportInterface` |
| `process_metadata_import` | `MetadataImportInterface` |
| `retry_metadata_search_item` | `MetadataImportInterface` |
| `process_metadata_export` | `MetadataExportInterface` |
| `remap_batch_attributes`, `remap_dataset_attributes` | mapper service only |
| `retry_stalled_jobs` | nothing, periodic self-healing |

## Deferring work from the web application

The web application never enqueues jobs directly. It goes through
[`Scheduler`](https://github.com/imi-bigpicture/slidetap/blob/main/slidetap-app/src/slidetap/task/scheduler.py),
which `WebAppProvider` supplies, with one method per unit of work
(`pre_process_images`, `post_process_images`, `metadata_batch_import`,
`metadata_project_export`, `store_images_in_batch`, and the remap and retry
entry points). `Scheduler` needs the Procrastinate `App`, which is why a web
app must also register `ProcrastinateAppProvider`.

## Queues and priority

Tasks are routed to one of three queues so that a long image conversion does
not hold up a quick remap:

- `image_processing` for download, conversion, and export of images.
- `metadata_import` for metadata search and import.
- `default` for everything else, including the recovery task.

Priority is set per task and orders dispatch within a queue: long-running work
is dispatched at low priority and latency-sensitive work such as retries and
remaps at high priority, so a freed worker slot picks up the short job first.

## Failure and retry

An implementation of an external interface signals that a task is worth
retrying by raising `TransientTaskError`. Such a task is retried up to three
times with exponentially growing waits. Any other exception is terminal: the
task ends in its failure path, which sets the failing item or batch to a failed
status and records the exception message, so the failure is visible in the web
client rather than silently swallowed.

Jobs left in progress by a worker that died are picked up by
`retry_stalled_jobs`, a periodic task that runs every five minutes, resets the
status of the affected items, and re-queues them. It takes a lock so that
overlapping ticks cannot race each other.

## Running a worker

A worker is started with the `slidetap-task-worker` console script. It reads
`concurrency` and `stalled_worker_timeout` from the `task:` section of
`config.yaml`, and locates the Procrastinate `App` through `SLIDETAP_TASK_APP`,
which is the dotted name of the package whose `task_app.py` exposes `task_app`:

```console
> SLIDETAP_TASK_APP=your_package uv run slidetap-task-worker
```

The worker refuses to start against a database that has not been migrated, so
`slidetap-db upgrade` and `slidetap-task-init-schema` must have been run first.
See the [back-end README](https://github.com/imi-bigpicture/slidetap/blob/main/slidetap-app/README.md)
for how to build the task application and apply migrations.

Run as many workers as you need. They share the queue through the database. The
image tasks and the remap tasks are idempotent under redelivery: an entry guard
inspects the current status and decides whether to run, take over from a dead
worker, or skip, so a job delivered twice does not do its work twice.
