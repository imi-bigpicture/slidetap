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

"""FastAPI router for health checks."""
import logging
from typing import Annotated

from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends

from slidetap.web.routers.dependencies import create_logger_dependency

health_router = APIRouter(
    prefix="/api/health",
    tags=["health"],
    route_class=DishkaRoute,
)

Logger = Annotated[logging.Logger, Depends(create_logger_dependency(__name__))]


@health_router.get("/status")
async def get_status(
    logger: Logger,
) -> dict[str, str]:
    """Get application health status."""
    logger.debug("Health check requested.")
    return {"status": "ok"}
