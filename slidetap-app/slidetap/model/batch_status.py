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

from enum import IntEnum


class BatchStatus(IntEnum):
    INITIALIZED = 1
    METADATA_SEARCHING = 2
    METADATA_SEARCH_COMPLETE = 3
    IMAGE_PRE_PROCESSING = 4
    IMAGE_PRE_PROCESSING_COMPLETE = 5
    IMAGE_POST_PROCESSING = 6
    IMAGE_POST_PROCESSING_COMPLETE = 7
    COMPLETED = 8
    FAILED = 10
    DELETED = 11
