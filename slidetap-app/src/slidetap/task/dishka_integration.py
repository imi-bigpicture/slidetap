#    Copyright 2024 SECTRA AB
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Dishka adapter for Procrastinate tasks.

Provides ``@dishka_task`` so task authors can annotate parameters with
``FromDishka[T]`` and have them resolved per call. The decorator
forwards to ``@app.task`` after wrapping the function with a resolver.

Container lifecycle:
- The APP-scope container is attached to the Procrastinate :class:`App`
  via :func:`setup_dishka` at task-app-factory time. Mirrors the
  ``setup_dishka(container, app)`` convention used by Dishka's other
  framework integrations.
- Each task entry opens a child REQUEST-scope container, resolves the
  marked parameters, calls the user function, and closes the scope.

Public API:
- ``FromDishka`` — re-exported from dishka; used as a parameter annotation.
- ``dishka_task(app, **task_kwargs)`` — task decorator.
- ``setup_dishka(container, app)`` — attach a container to a worker App.
"""

from __future__ import annotations

import functools
import inspect
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    List,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
)

from dishka import Container, FromDishka
from dishka.entities.key import _FromComponent
from procrastinate import App as TaskApp
from procrastinate import Blueprint, JobContext


def _find_dishka_params(fn: Callable[..., Any]) -> List[Tuple[str, Type[Any]]]:
    """Return list of (param_name, service_type) for FromDishka-annotated args.

    ``FromDishka[T]`` lowers to ``Annotated[T, _FromComponent(...)]``, so
    detection matches the same shape Dishka's official integrations
    expect.
    """
    hints = inspect.get_annotations(fn, eval_str=True)
    found: List[Tuple[str, Type[Any]]] = []
    for name, annotation in hints.items():
        if name == "return":
            continue
        if get_origin(annotation) is not Annotated:
            continue
        args = get_args(annotation)
        if not any(
            isinstance(arg, (FromDishka, _FromComponent)) for arg in args[1:]
        ):
            continue
        found.append((name, args[0]))
    return found


def dishka_task(
    target: Union[TaskApp, Blueprint],
    *,
    name: str,
    queue: str = "default",
    inject_task_id: bool = False,
    **task_kwargs: Any,
) -> Callable[[Callable[..., Any]], Any]:
    """Register a Procrastinate task with Dishka-resolved parameters.

    ``target`` is either an :class:`App` or a :class:`Blueprint`. Both
    expose ``.task(...)`` with the same signature.

    Usage::

        @dishka_task(blueprint, name="my_task", queue="default")
        def my_task(
            arg: UUID,
            service: FromDishka[MyService],
        ) -> None:
            ...

    Callers invoke ``my_task.defer(arg=...)`` with only the non-injected
    kwargs. The wrapper opens a Dishka request scope, resolves
    ``service`` from the worker's container, and calls the user function.

    When ``inject_task_id=True``, the wrapper passes ``str(context.job.id)``
    as the ``task_id`` parameter — useful for tasks that need a stable
    "who's currently holding this resource" marker.
    """

    def decorator(fn: Callable[..., Any]) -> Any:
        dishka_params = _find_dishka_params(fn)
        synthetic_names = {name for name, _ in dishka_params}
        if inject_task_id:
            synthetic_names.add("task_id")

        # Function signature minus the injected parameters — what callers pass.
        signature = inspect.signature(fn)
        caller_params = [
            param for param_name, param in signature.parameters.items()
            if param_name not in synthetic_names
        ]

        @functools.wraps(fn)
        def wrapper(context: JobContext, **kwargs: Any) -> Any:
            container = container_from_app(context.app)
            with container() as request_container:
                resolved: Dict[str, Any] = {}
                for param_name, service_type in dishka_params:
                    resolved[param_name] = request_container.get(service_type)
                if inject_task_id:
                    resolved["task_id"] = str(context.job.id)
                return fn(**kwargs, **resolved)

        # Procrastinate inspects the wrapper signature for argument names.
        # Strip the injected params so .defer(...) callers see the clean API.
        wrapper.__signature__ = signature.replace(parameters=caller_params)  # type: ignore[attr-defined]

        return target.task(
            name=name,
            queue=queue,
            pass_context=True,
            **task_kwargs,
        )(wrapper)

    return decorator


_CONTAINER_ATTR = "_slidetap_container"


def setup_dishka(container: Container, app: TaskApp) -> None:
    """Attach ``container`` to ``app`` so task wrappers can resolve it.

    Mirrors the ``setup_dishka(container, app)`` convention used by
    Dishka's other framework integrations (Celery, FastAPI, Flask, ...).
    """
    setattr(app, _CONTAINER_ATTR, container)


def container_from_app(app: TaskApp) -> Container:
    """Return the container previously attached by :func:`setup_dishka`."""
    container = getattr(app, _CONTAINER_ATTR, None)
    if not isinstance(container, Container):
        raise RuntimeError(
            "App has no attached Dishka container — call setup_dishka() "
            "after building the App."
        )
    return container
