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

from alembic.script import ScriptDirectory
from slidetap.migrations.cli import config


def test_config_finds_migrations_without_alembic_ini():
    """The in-code configuration resolves the migrations shipped in the package.

    This is what lets deployments run slidetap-db-upgrade from any working
    directory, so it breaks if script_location or the packaged versions/ go
    missing.
    """
    scripts = ScriptDirectory.from_config(config())

    assert scripts.get_current_head() is not None
