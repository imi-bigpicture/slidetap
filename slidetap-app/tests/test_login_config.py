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

import pytest

from slidetap.config import MIN_SECRET_KEY_BYTES, LoginConfig


@pytest.mark.unittest
class TestLoginConfig:
    def test_key_of_the_minimum_length_is_accepted(self):
        # Arrange
        secret_key = "k" * MIN_SECRET_KEY_BYTES

        # Act
        config = LoginConfig(secret_key)

        # Assert
        assert config.secret_key == secret_key

    @pytest.mark.parametrize("secret_key", ["", "DEVELOP", "k" * 31])
    def test_shorter_key_is_refused(self, secret_key: str):
        with pytest.raises(ValueError, match="SLIDETAP_SECRET_KEY"):
            LoginConfig(secret_key)

    def test_length_is_counted_in_bytes(self):
        # Sixteen two-byte characters make 32 bytes.
        LoginConfig("å" * 16)
