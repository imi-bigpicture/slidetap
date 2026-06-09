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

"""Exception types signalled by external-interface implementations."""


class TransientTaskError(Exception):
    """Raised by an external-interface implementation when a failure is
    transient and the task should be retried with backoff.

    Tasks are decorated with a Procrastinate retry strategy that triggers
    only on this exception class. Implementations are expected to wrap
    their library-specific transient errors (network timeouts, upstream
    5xx, DB deadlocks, ...) with ``raise TransientTaskError(...) from exc``
    so the original traceback is preserved.

    Any other unhandled exception will mark the job FAILED.
    """
