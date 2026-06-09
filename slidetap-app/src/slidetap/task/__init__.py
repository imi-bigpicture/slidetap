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

"""Background task layer, backed by Procrastinate.

The Procrastinate :class:`App` is provided through Dishka — see
:class:`ProcrastinateAppProvider`. Tasks register against
:data:`slidetap.task.tasks.slidetap_tasks` at import time and are
attached when the App is constructed.

Workers run via the ``slidetap-task-worker`` console script (see
:mod:`slidetap.task.worker_cli`), which reads ``TaskConfig`` from YAML
and invokes :meth:`App.run_worker` against the deployment's task-app
factory output. Procrastinate's own ``procrastinate worker`` CLI is
still available for ad-hoc runs.
"""

from slidetap.task.app_factory import SlideTapTaskAppFactory
from slidetap.task.scheduler import Scheduler
from slidetap.task.service_provider import ProcrastinateAppProvider, TaskAppProvider

__all__ = [
    "ProcrastinateAppProvider",
    "Scheduler",
    "SlideTapTaskAppFactory",
    "TaskAppProvider",
]
