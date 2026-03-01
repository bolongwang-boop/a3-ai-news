from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ── Health endpoint ────────────────────────────────────────────

class TestHealthEndpoint:
    @patch("src.main.settings")
    def test_database_enabled(self, mock_settings):
        mock_settings.database_url = "postgresql+asyncpg://localhost/test"
        mock_settings.enable_persistence = True
        mock_settings.newsapi_key = None

        from src.main import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["database"] == "enabled"

    @patch("src.main.settings")
    def test_database_disabled(self, mock_settings):
        mock_settings.database_url = None
        mock_settings.enable_persistence = False
        mock_settings.newsapi_key = None

        from src.main import app

        client = TestClient(app, raise_server_exceptions=False)
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["database"] == "disabled"


# ── Lifespan ───────────────────────────────────────────────────

class TestLifespan:
    @pytest.mark.asyncio
    @patch("src.main.settings")
    async def test_startup_without_db(self, mock_settings):
        mock_settings.database_url = None
        mock_settings.enable_persistence = False
        mock_settings.newsapi_key = None

        from src.main import lifespan

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        async with lifespan(mock_app):
            assert mock_app.state.aggregator is not None
            assert mock_app.state.repository is None

    @pytest.mark.asyncio
    @patch("src.main.settings")
    async def test_startup_with_db(self, mock_settings):
        mock_settings.database_url = "postgresql+asyncpg://localhost/test"
        mock_settings.enable_persistence = True
        mock_settings.newsapi_key = None
        mock_settings.database_pool_size = 5
        mock_settings.database_max_overflow = 10

        mock_conn = AsyncMock()
        begin_ctx = MagicMock()
        begin_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        begin_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_engine = MagicMock()
        mock_engine.begin.return_value = begin_ctx
        mock_engine.dispose = AsyncMock()

        with (
            patch("src.database.connection.get_engine", return_value=mock_engine),
            patch("src.database.connection.get_session_factory", return_value=MagicMock()),
            patch("src.database.models.Base.metadata"),
        ):
            from src.main import lifespan

            mock_app = MagicMock()
            mock_app.state = MagicMock()

            async with lifespan(mock_app):
                assert mock_app.state.repository is not None

    @pytest.mark.asyncio
    @patch("src.main.settings")
    async def test_startup_db_failure_fallback(self, mock_settings):
        mock_settings.database_url = "postgresql+asyncpg://localhost/test"
        mock_settings.enable_persistence = True
        mock_settings.newsapi_key = None
        mock_settings.database_pool_size = 5
        mock_settings.database_max_overflow = 10

        with patch("src.database.connection.get_engine", side_effect=Exception("connection refused")):
            from src.main import lifespan

            mock_app = MagicMock()
            mock_app.state = MagicMock()

            async with lifespan(mock_app):
                # Should fall back to no repository
                assert mock_app.state.repository is None

    @pytest.mark.asyncio
    @patch("src.main.settings")
    async def test_shutdown_closes_client(self, mock_settings):
        mock_settings.database_url = None
        mock_settings.enable_persistence = False
        mock_settings.newsapi_key = None

        from src.main import lifespan

        mock_app = MagicMock()
        mock_app.state = MagicMock()

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value = mock_client

            async with lifespan(mock_app):
                pass

            mock_client.aclose.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("src.main.settings")
    async def test_shutdown_disposes_engine(self, mock_settings):
        mock_settings.database_url = "postgresql+asyncpg://localhost/test"
        mock_settings.enable_persistence = True
        mock_settings.newsapi_key = None
        mock_settings.database_pool_size = 5
        mock_settings.database_max_overflow = 10

        mock_conn = AsyncMock()
        begin_ctx = MagicMock()
        begin_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        begin_ctx.__aexit__ = AsyncMock(return_value=False)

        mock_engine = MagicMock()
        mock_engine.begin.return_value = begin_ctx
        mock_engine.dispose = AsyncMock()

        with (
            patch("src.database.connection.get_engine", return_value=mock_engine),
            patch("src.database.connection.get_session_factory", return_value=MagicMock()),
            patch("src.database.models.Base.metadata"),
        ):
            from src.main import lifespan

            mock_app = MagicMock()
            mock_app.state = MagicMock()

            async with lifespan(mock_app):
                pass

            mock_engine.dispose.assert_awaited_once()
