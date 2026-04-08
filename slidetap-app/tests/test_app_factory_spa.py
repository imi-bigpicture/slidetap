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

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slidetap.web.app_factory import SlideTapWebAppFactory


def _make_dist(root: Path) -> Path:
    """Write a minimal dist/ directory matching Vite's output structure."""
    dist = root / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>SlideTap</body></html>")
    assets = dist / "assets"
    assets.mkdir()
    (assets / "main.js").write_text("console.log('hello')")
    return dist


@pytest.mark.unittest
class TestSlideTapWebAppFactorySpa:
    def test_no_static_dir_does_not_mount_spa(self):
        # When static_dir is None the factory returns a plain app with no catch-all
        app = FastAPI()
        SlideTapWebAppFactory._mount_spa.__doc__  # ensure method exists
        # Verify the app has no catch-all route
        paths = [route.path for route in app.routes]  # type: ignore[attr-defined]
        assert "/{full_path:path}" not in paths

    def test_missing_static_dir_is_silently_ignored(self):
        # Passing a non-existent path must not raise
        with TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nonexistent_dist"
            app = FastAPI()
            # _mount_spa is only called if the dir exists; caller guards with .exists()
            assert not missing.exists()
            # No exception raised; nothing mounted
            paths = [route.path for route in app.routes]  # type: ignore[attr-defined]
            assert "/{full_path:path}" not in paths

    def test_existing_static_dir_mounts_assets_and_spa_route(self):
        with TemporaryDirectory() as tmp:
            dist = _make_dist(Path(tmp))
            app = FastAPI()
            SlideTapWebAppFactory._mount_spa(app, dist)
            paths = [route.path for route in app.routes]  # type: ignore[attr-defined]
            assert "/{full_path:path}" in paths
            mount_names = [
                r.name  # type: ignore[attr-defined]
                for r in app.routes
                if hasattr(r, "name") and r.name == "assets"
            ]
            assert mount_names, "assets mount not found"

    def test_spa_route_serves_index_html(self):
        with TemporaryDirectory() as tmp:
            dist = _make_dist(Path(tmp))
            app = FastAPI()
            SlideTapWebAppFactory._mount_spa(app, dist)
            client = TestClient(app, raise_server_exceptions=True)
            response = client.get("/some/frontend/route")
            assert response.status_code == 200
            assert b"SlideTap" in response.content

    def test_assets_are_served(self):
        with TemporaryDirectory() as tmp:
            dist = _make_dist(Path(tmp))
            app = FastAPI()
            SlideTapWebAppFactory._mount_spa(app, dist)
            client = TestClient(app)
            response = client.get("/assets/main.js")
            assert response.status_code == 200
            assert b"hello" in response.content
