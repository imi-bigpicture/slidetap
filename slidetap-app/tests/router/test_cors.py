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

"""Tests for CORS configured from origins read when the app starts."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from slidetap.web.app_factory import ConfiguredCorsMiddleware, SlideTapWebAppFactory


def _app(cors_origins: str | None) -> FastAPI:
    """An app that, like the SlideTap app, reads its CORS origins at startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.cors_origins = SlideTapWebAppFactory._parse_cors_origins(cors_origins)
        yield

    app = FastAPI(lifespan=lifespan)
    app.add_middleware(ConfiguredCorsMiddleware)

    @app.get("/ping")
    def ping() -> str:
        return "pong"

    return app


def _preflight(client: TestClient, origin: str):
    return client.options(
        "/ping",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )


@pytest.mark.unittest
class TestConfiguredCors:
    def test_app_with_origins_starts_and_allows_each_origin(self):
        # Arrange
        app = _app("http://first.example, http://second.example")

        # Act
        with TestClient(app) as client:
            first = _preflight(client, "http://first.example")
            second = _preflight(client, "http://second.example")

        # Assert
        assert first.headers["access-control-allow-origin"] == "http://first.example"
        assert second.headers["access-control-allow-origin"] == "http://second.example"

    def test_origin_not_configured_is_not_allowed(self):
        # Arrange
        app = _app("http://first.example")

        # Act
        with TestClient(app) as client:
            response = _preflight(client, "http://other.example")

        # Assert
        assert "access-control-allow-origin" not in response.headers

    def test_without_origins_requests_pass_through(self):
        # Arrange
        app = _app(None)

        # Act
        with TestClient(app) as client:
            response = client.get("/ping", headers={"Origin": "http://first.example"})

        # Assert
        assert response.json() == "pong"
        assert "access-control-allow-origin" not in response.headers

    @pytest.mark.parametrize(
        ["cors_origins", "expected"],
        [
            (None, []),
            ("", []),
            ("http://a.example", ["http://a.example"]),
            (
                " http://a.example ,, http://b.example ",
                ["http://a.example", "http://b.example"],
            ),
        ],
    )
    def test_parse_cors_origins(self, cors_origins: str | None, expected: list[str]):
        assert SlideTapWebAppFactory._parse_cors_origins(cors_origins) == expected
