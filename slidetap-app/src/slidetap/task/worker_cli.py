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

"""Console-script entry point for the Procrastinate worker.

Reads worker tuning from ``config.yaml`` under ``task:`` (via
:class:`TaskConfig`) and runs the worker programmatically, so worker
behaviour lives alongside the rest of the app config instead of being
threaded through ``.env`` into the docker-compose ``command:`` array.

Environment:
    ``SLIDETAP_TASK_APP`` — dotted package name whose ``task_app.py``
    exposes ``task_app`` (the configured Procrastinate :class:`App`).
    ``SLIDETAP_CONFIG_FILE`` — path to the YAML config, read by
    :class:`ConfigParser`.
"""

import importlib
import os

from procrastinate import App as TaskApp

from slidetap.config import ConfigParser, TaskConfig


def main() -> None:
    config = TaskConfig.parse(ConfigParser.create())
    module = importlib.import_module(f"{os.environ['SLIDETAP_TASK_APP']}.task_app")
    task_app: TaskApp = module.task_app
    task_app.run_worker(
        concurrency=config.concurrency,
        stalled_worker_timeout=config.stalled_worker_timeout,
        install_signal_handlers=True,
    )


if __name__ == "__main__":
    main()
