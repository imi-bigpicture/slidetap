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

"""Shared FastAPI dependencies for routers."""

import logging
from typing import Callable


def create_logger_dependency(module_name: str) -> Callable[[], logging.Logger]:
    """Create a logger dependency factory for a specific module.


    Parameters
    ----------
    module_name : str
        The module name, typically passed as __name__ from the router file.

    Returns
    -------
    Callable[[], logging.Logger]
        A dependency function that returns a logger for the module.
    """

    def get_logger() -> logging.Logger:
        return logging.getLogger(module_name)

    return get_logger
