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


class MapperInjectionError(Exception):
    """Raised by a mapper injector that cannot build the mappers it was
    configured with.

    A configuration error, not a data error: what the deployment declared is
    wrong, so injection stops rather than coming up with a silently incomplete
    set of mappers. A problem in a single mapping row that the injector can
    skip stays a warning.

    The parts are kept as fields rather than only formatted into the message,
    so that what surfaces the error --- a log line today, a health check or the
    mapper group view later --- can present them as it likes.
    """

    def __init__(
        self,
        reason: str,
        *,
        injector: str,
        mapper: str | None = None,
        source: str | None = None,
    ) -> None:
        """Create a mapper injection error.

        Parameters
        ----------
        reason: str
            What is wrong, phrased so that it reads after the location.
        injector: str
            The injector that could not build the mapper, so that a deployment
            injecting from more than one place says which.
        mapper: str | None
            The name the mapper is declared under, if the failure is on one
            mapper rather than the load as a whole.
        source: str | None
            Where it is declared, in whatever way the injector locates it: a
            sheet name, a file, a pointer into one.
        """
        self.reason = reason
        self.injector = injector
        self.mapper = mapper
        self.source = source
        super().__init__(self._message())

    def _message(self) -> str:
        located = self.injector
        if self.mapper is not None:
            located += f" mapper '{self.mapper}'"
        if self.source is not None:
            located += f" in '{self.source}'"
        return f"{located}: {self.reason}"
