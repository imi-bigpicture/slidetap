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
from typing import Optional

from dishka import Provider, Scope

from slidetap.service_provider import CallableOrType
from slidetap.services import (
    BasicAuthService,
    ImageCache,
    ImageService,
    MapperInjector,
)
from slidetap.task.scheduler import Scheduler
from slidetap.web.services import (
    ImageExportService,
    ImageImportService,
    LoginService,
    MetadataExportService,
    MetadataImportService,
)


class WebAppProvider(Provider):
    def __init__(
        self,
        auth_service: CallableOrType[BasicAuthService],
        mapper_injector: CallableOrType[Optional[MapperInjector]] = lambda: None,
    ):
        super().__init__(scope=Scope.APP)
        self.provide(mapper_injector, provides=Optional[MapperInjector])
        self.provide(auth_service, provides=BasicAuthService)
        self.provide(LoginService)
        self.provide(ImageService)
        self.provide(ImageCache)
        self.provide(Scheduler)
        self.provide(MetadataImportService)
        self.provide(MetadataExportService)
        self.provide(ImageImportService)
        self.provide(ImageExportService)
