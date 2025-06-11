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


from slidetap.web.services.auth import (
    AuthService,
    BasicAuthService,
    HardCodedBasicAuthTestService,
)
from slidetap.web.services.image_export_service import ImageExportService
from slidetap.web.services.image_import_service import ImageImportService
from slidetap.web.services.login import LoginService
from slidetap.web.services.metadata_export_service import MetadataExportService
from slidetap.web.services.metadata_import_service import MetadataImportService
