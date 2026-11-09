#    Copyright 2026 SECTRA AB
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

"""FastAPI router for how the application behaves."""

from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, Depends

from slidetap.application_policy import ApplicationPolicy
from slidetap.web.services.login_service import require_valid_token

application_router = APIRouter(
    prefix="/api/application",
    tags=["application"],
    route_class=DishkaRoute,
    dependencies=[Depends(require_valid_token)],
)


@application_router.get("/policy")
def get_policy(
    application_policy: FromDishka[ApplicationPolicy],
) -> ApplicationPolicy:
    """How the application behaves, as its plugin is built, such as whether
    its images are pre-processed in a step of their own.

    Returns
    ----------
    ApplicationPolicy
        The same for every project.
    """
    return application_policy
