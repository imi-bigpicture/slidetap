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

"""Factory for creating a Procrastinate worker app to run."""

from dishka import Container
from procrastinate import App as TaskApp

from slidetap.task.dishka_integration import setup_dishka


class SlideTapTaskAppFactory:
    """Factory for creating a Procrastinate App to run workers against."""

    @classmethod
    def create(
        cls,
        container: Container,
    ) -> TaskApp:
        """Return the container's App with the container attached.

        Parameters
        ----------
        container : Container
            Dependency injection container for the application.

        Returns
        ----------
        TaskApp
            Procrastinate App the ``procrastinate worker`` CLI loads.

        """
        task_app = container.get(TaskApp)
        setup_dishka(container=container, app=task_app)
        return task_app
