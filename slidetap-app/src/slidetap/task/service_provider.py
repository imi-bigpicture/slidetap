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

"""Dishka provider exposing the task layer's APP-scoped services."""

from typing import Callable, Optional

from dishka import Provider, Scope
from procrastinate import App as TaskApp
from procrastinate import PsycopgConnector

from slidetap.config import TaskConfig
from slidetap.external_interfaces import (
    ImageExportInterface,
    ImageImportInterface,
)
from slidetap.task.heartbeat import ImageHeartbeat
from slidetap.task.tasks import slidetap_tasks


class ProcrastinateAppProvider(Provider):
    def __init__(
        self,
        app_factory: Optional[Callable[[TaskConfig], TaskApp]] = None,
    ):
        super().__init__(scope=Scope.APP)
        self.provide(app_factory or self._make_default_app, provides=TaskApp)

    @staticmethod
    def _make_default_app(config: TaskConfig) -> TaskApp:
        """Default Procrastinate App factory — psycopg connector + tasks.

        Workers must call
        :func:`slidetap.task.dishka_integration.setup_dishka` on the
        returned App so tasks can resolve their Dishka services at runtime.
        """
        app = TaskApp(connector=PsycopgConnector(conninfo=config.db_uri))
        app.add_tasks_from(slidetap_tasks, namespace="slidetap")
        return app


class TaskAppProvider(Provider):
    def __init__(
        self,
        image_import_interface: Callable[..., ImageImportInterface],
        image_export_interface: Callable[..., ImageExportInterface],
    ):
        super().__init__(scope=Scope.APP)
        self.provide(image_import_interface, provides=ImageImportInterface)
        self.provide(image_export_interface, provides=ImageExportInterface)
        self.provide(ImageHeartbeat)
