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

"""Module containing services for authenticating user."""
from slidetap.web.services.auth.auth_service import (
    AuthService,
    AuthServiceException,
)
from slidetap.web.services.auth.basic_auth_service import BasicAuthService
from slidetap.web.services.auth.hardcoded_basic_auth_service import (
    HardCodedBasicAuthTestService,
)
from slidetap.web.services.auth.oauth_auth_service import (
    OauthAuthService,
    OpenIdAuthService,
)
