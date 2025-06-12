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


from fastapi import Request, Response
from slidetap.web.services.login_service import LoginService


class DummyLoginService(LoginService):
    def verify_access_and_csrf_tokens(self, request: Request):
        return "user"

    def set_login_cookies(self, response: Response, user: str):
        pass

    def unset_login_cookies(self, response: Response):
        pass
