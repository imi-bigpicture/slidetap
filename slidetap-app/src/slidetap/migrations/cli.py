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

"""Upgrade the SlideTap database to the latest migration.

The configuration is built in code rather than read from alembic.ini, so the
command works from any working directory in any deployment that installs
slidetap. alembic.ini is for development commands such as
``alembic revision --autogenerate``.

Environment:
    ``SLIDETAP_DBURI`` -- database URL for the target database, read by
        ``migrations/env.py``.
"""

import logging
import os
import sys

from alembic import command
from alembic.config import Config


def config() -> Config:
    """Alembic configuration pointing at the migrations shipped with the package."""
    config = Config()
    config.set_main_option("script_location", "slidetap:migrations")
    return config


def main() -> None:
    if not os.environ.get("SLIDETAP_DBURI"):
        print("SLIDETAP_DBURI is not set.", file=sys.stderr)
        raise SystemExit(1)
    # env.py only configures logging when run through alembic.ini, so set up the
    # same levels here to keep the per-revision progress lines visible.
    logging.basicConfig(
        level=logging.WARNING, format="%(levelname)-5.5s [%(name)s] %(message)s"
    )
    logging.getLogger("alembic").setLevel(logging.INFO)
    command.upgrade(config(), "head")


if __name__ == "__main__":
    main()
