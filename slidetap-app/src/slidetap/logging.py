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

from logging.config import dictConfig
from typing import Any, Dict, Literal, Optional

LogLevel = Literal["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]


def setup_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Configure stdlib logging from a ``logging.config.dictConfig`` schema.

    No-op when ``config`` is ``None`` — leaves whatever level/handlers
    callers set directly (or Python's defaults) in place. Used to opt
    into a full ``dictConfig``-style logging setup via the ``logging:``
    section of ``config.yaml``.
    """
    if config is None:
        return
    dictConfig(config)
