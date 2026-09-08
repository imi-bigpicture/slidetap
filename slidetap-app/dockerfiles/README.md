# Back-end Dockerfiles

Images for the two back-end processes. Both are built with `slidetap-app` as
the build context, and both install the library and the example app, so they
run the example application out of the box. To ship your own application,
replace the second `pip install` with your own distribution.

| File | Image | Runs |
|---|---|---|
| `webservice.Dockerfile` | FastAPI web application | `uvicorn "${SLIDETAP_WEB_APP}"` |
| `taskservice.Dockerfile` | Procrastinate worker | `slidetap-task-worker` |

The front-end has its own image, built from `slidetap-client/dockerfiles/`,
which serves the built client and terminates SSL with nginx.

## Building

The `example/docker-compose.yml` stack builds both from this folder, so nothing
needs to be built by hand to run the example:

```yaml
build:
  context: ../slidetap-app
  dockerfile: dockerfiles/webservice.Dockerfile
```

Standalone, from the `slidetap-app` folder:

```console
> docker build -t slidetap-webservice -f dockerfiles/webservice.Dockerfile .
> docker build -t slidetap-taskservice -f dockerfiles/taskservice.Dockerfile .
```

## Runtime configuration

Neither image bakes in any configuration. Both need `SLIDETAP_CONFIG_FILE`
pointing at a mounted `config.yaml`, `SLIDETAP_DBURI`, `SLIDETAP_STORAGE`, and
`SLIDETAP_SECRET_KEY`; see the [back-end
README](../README.md#configuration-of-application) for the full set. Beyond
those, each image reads one variable of its own:

- `webservice.Dockerfile` needs `SLIDETAP_WEB_APP`, the uvicorn target of the
  FastAPI app as `package.module:attribute`, and `SLIDETAP_APIPORT`, the port
  it listens on.
- `taskservice.Dockerfile` needs `SLIDETAP_TASK_APP`, the dotted name of the
  package whose `task_app.py` exposes `task_app`. Not a module path and not an
  attribute reference.

## Migrations

Migrations are an explicit deploy step, and both processes refuse to start
against a database that has not had them applied. The task image also carries
the migration commands, so the compose stack runs it a third time as a one-shot
service that the other two wait for:

```yaml
dbmigrate:
  build:
    context: ../slidetap-app
    dockerfile: dockerfiles/taskservice.Dockerfile
  command: >
    sh -c "slidetap-db upgrade &&
           slidetap-task-init-schema"
  restart: "no"
```

Both commands are idempotent, so this is safe on every boot.

## Notes

The images install the packages in editable mode against the copied source, and
the web image installs the example app's `[web]` extra. `libturbojpeg0` is
installed for image reading; the OpenSlide and build-toolchain lines are
commented out, and need uncommenting if your image import or export needs them.
