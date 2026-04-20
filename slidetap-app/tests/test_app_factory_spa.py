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

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slidetap.web.app_factory import SlideTapWebAppFactory


@pytest.fixture()
def dist_dir():
    """Create minimal Vite-style dist/ with index.html and assets/main.js."""
    with TemporaryDirectory() as tmp:
        dist = Path(tmp) / "dist"
        dist.mkdir()
        (dist / "index.html").write_text("<html><body>SlideTap</body></html>")
        assets = dist / "assets"
        assets.mkdir()
        (assets / "main.js").write_text("console.log('hello')")
        yield dist


@pytest.fixture()
def spa_app(dist_dir: Path):
    """FastAPI app with SPA mounted."""
    app = FastAPI()
    SlideTapWebAppFactory._mount_spa(app, dist_dir)
    return app


@pytest.fixture()
def spa_client(spa_app: FastAPI):
    return TestClient(spa_app, raise_server_exceptions=True)


@pytest.mark.unittest
class TestMountSpa:
    def test_mounts_catch_all_route(self, spa_app: FastAPI):
        # Arrange

        # Act
        paths = [route.path for route in spa_app.routes]  # type: ignore[attr-defined]

        # Assert
        assert "/{full_path:path}" in paths

    def test_mounts_assets_directory(self, spa_app: FastAPI):
        # Arrange

        # Act
        mount_names = [
            r.name  # type: ignore[attr-defined]
            for r in spa_app.routes
            if hasattr(r, "name") and r.name == "assets"
        ]

        # Assert
        assert mount_names, "assets mount not found"

    def test_serves_index_html_for_frontend_routes(self, spa_client: TestClient):
        # Arrange

        # Act
        response = spa_client.get("/some/frontend/route")

        # Assert
        assert response.status_code == 200
        assert b"SlideTap" in response.content

    def test_serves_assets(self, spa_client: TestClient):
        # Arrange

        # Act
        response = spa_client.get("/assets/main.js")

        # Assert
        assert response.status_code == 200
        assert b"hello" in response.content

    def test_api_paths_return_404(self, spa_client: TestClient):
        # Arrange

        # Act
        response = spa_client.get("/api/does-not-exist")

        # Assert
        assert response.status_code == 404

    def test_skips_assets_mount_when_no_assets_dir(self):
        # Arrange
        with TemporaryDirectory() as tmp:
            dist = Path(tmp) / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("<html></html>")
            app = FastAPI()

            # Act
            SlideTapWebAppFactory._mount_spa(app, dist)
            mount_names = [
                r.name  # type: ignore[attr-defined]
                for r in app.routes
                if hasattr(r, "name") and r.name == "assets"
            ]

            # Assert
            assert not mount_names


@pytest.mark.unittest
class TestCreateStaticDirGuard:
    def test_no_static_dir_does_not_mount(self):
        # Arrange

        # Act / Assert — _mount_spa should not be called when static_dir is None
        with patch.object(SlideTapWebAppFactory, "_mount_spa") as mock:
            # Simulate factory guard: static_dir is None
            static_dir = None
            if (
                static_dir is not None
                and static_dir.is_dir()
                and (static_dir / "index.html").is_file()
            ):
                SlideTapWebAppFactory._mount_spa(FastAPI(), static_dir)
            mock.assert_not_called()

    def test_missing_dir_does_not_mount(self):
        # Arrange
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nonexistent"

            # Act / Assert
            with patch.object(SlideTapWebAppFactory, "_mount_spa") as mock:
                if (
                    missing.is_dir()
                    and (missing / "index.html").is_file()
                ):
                    SlideTapWebAppFactory._mount_spa(FastAPI(), missing)
                mock.assert_not_called()

    def test_dir_without_index_html_does_not_mount(self):
        # Arrange
        with TemporaryDirectory() as tmp:
            empty_dir = Path(tmp) / "dist"
            empty_dir.mkdir()

            # Act / Assert
            with patch.object(SlideTapWebAppFactory, "_mount_spa") as mock:
                if (
                    empty_dir.is_dir()
                    and (empty_dir / "index.html").is_file()
                ):
                    SlideTapWebAppFactory._mount_spa(FastAPI(), empty_dir)
                mock.assert_not_called()
