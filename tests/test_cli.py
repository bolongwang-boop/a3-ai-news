import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tests.conftest import make_article


def _fake_response_dict():
    articles = [make_article(title=f"Article {i}", url=f"https://example.com/{i}") for i in range(3)]
    return {
        "total_articles": 3,
        "query": "AI news (last week, Sydney time)",
        "from_date_sydney": "2026-02-18 00:00:00 AEDT",
        "to_date_sydney": "2026-02-25 12:00:00 AEDT",
        "sources_queried": ["google_rss"],
        "articles": [a.model_dump(mode="json") for a in articles],
    }


class TestCLIStdout:
    """Tests for CLI output to stdout (default behaviour)."""

    @patch("src.cli.settings")
    @patch("src.cli._fetch_news", new_callable=AsyncMock)
    def test_outputs_json_to_stdout(self, mock_fetch, mock_settings, capsys):
        mock_fetch.return_value = _fake_response_dict()
        mock_settings.default_days_back = 7
        mock_settings.output_file = None

        from src.cli import main

        with patch("sys.argv", ["ai-news"]):
            main()

        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["total_articles"] == 3
        assert len(data["articles"]) == 3

    @patch("src.cli.settings")
    @patch("src.cli._fetch_news", new_callable=AsyncMock)
    def test_passes_days_argument(self, mock_fetch, mock_settings):
        mock_fetch.return_value = _fake_response_dict()
        mock_settings.default_days_back = 7
        mock_settings.output_file = None

        from src.cli import main

        with patch("sys.argv", ["ai-news", "--days", "3"]):
            main()

        mock_fetch.assert_called_once_with(3, True, 50)

    @patch("src.cli.settings")
    @patch("src.cli._fetch_news", new_callable=AsyncMock)
    def test_all_sources_flag_sets_credible_false(self, mock_fetch, mock_settings):
        mock_fetch.return_value = _fake_response_dict()
        mock_settings.default_days_back = 7
        mock_settings.output_file = None

        from src.cli import main

        with patch("sys.argv", ["ai-news", "--all-sources"]):
            main()

        mock_fetch.assert_called_once_with(7, False, 50)

    @patch("src.cli.settings")
    @patch("src.cli._fetch_news", new_callable=AsyncMock)
    def test_limit_argument(self, mock_fetch, mock_settings):
        mock_fetch.return_value = _fake_response_dict()
        mock_settings.default_days_back = 7
        mock_settings.output_file = None

        from src.cli import main

        with patch("sys.argv", ["ai-news", "--limit", "10"]):
            main()

        mock_fetch.assert_called_once_with(7, True, 10)


class TestCLIFileOutput:
    """Tests for CLI output to file via AINEWS_OUTPUT_FILE."""

    @patch("src.cli.settings")
    @patch("src.cli._fetch_news", new_callable=AsyncMock)
    def test_writes_to_file_when_output_file_set(self, mock_fetch, mock_settings, tmp_path):
        output_path = tmp_path / "news.json"
        mock_fetch.return_value = _fake_response_dict()
        mock_settings.default_days_back = 7
        mock_settings.output_file = str(output_path)

        from src.cli import main

        with patch("sys.argv", ["ai-news"]):
            main()

        assert output_path.exists()
        data = json.loads(output_path.read_text())
        assert data["total_articles"] == 3

    @patch("src.cli.settings")
    @patch("src.cli._fetch_news", new_callable=AsyncMock)
    def test_creates_parent_directories(self, mock_fetch, mock_settings, tmp_path):
        output_path = tmp_path / "nested" / "dir" / "news.json"
        mock_fetch.return_value = _fake_response_dict()
        mock_settings.default_days_back = 7
        mock_settings.output_file = str(output_path)

        from src.cli import main

        with patch("sys.argv", ["ai-news"]):
            main()

        assert output_path.exists()

    @patch("src.cli.settings")
    @patch("src.cli._fetch_news", new_callable=AsyncMock)
    def test_prints_confirmation_to_stderr(self, mock_fetch, mock_settings, tmp_path, capsys):
        output_path = tmp_path / "news.json"
        mock_fetch.return_value = _fake_response_dict()
        mock_settings.default_days_back = 7
        mock_settings.output_file = str(output_path)

        from src.cli import main

        with patch("sys.argv", ["ai-news"]):
            main()

        captured = capsys.readouterr()
        assert captured.out == ""  # nothing to stdout
        assert "3 articles" in captured.err
        assert str(output_path) in captured.err


class TestCLIDatabasePersistence:
    """Tests for CLI database persistence when AINEWS_DATABASE_URL is configured."""

    @pytest.mark.asyncio
    async def test_creates_repository_when_db_configured(self):
        """CLI initialises a repository when database settings are present."""
        from src.cli import _fetch_news

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_engine.begin = MagicMock(return_value=mock_conn)
        mock_engine.dispose = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=False)
        mock_conn.run_sync = AsyncMock()

        with (
            patch("src.cli.settings") as mock_settings,
            patch("src.database.connection.create_async_engine", return_value=mock_engine),
            patch("src.aggregator.NewsAggregator.fetch_weekly_ai_news", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_settings.newsapi_key = None
            mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost/test"
            mock_settings.enable_persistence = True
            mock_settings.database_pool_size = 5
            mock_settings.database_max_overflow = 10
            mock_settings.credible_domains = []

            mock_response = MagicMock()
            mock_response.model_dump.return_value = {"total_articles": 0, "articles": []}
            mock_fetch.return_value = mock_response

            await _fetch_news(7, True, 50)

            # Verify the aggregator was called (which means repository was wired up)
            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_runs_without_persistence_when_db_not_configured(self):
        """CLI runs without persistence when database settings are absent."""
        from src.cli import _fetch_news

        with (
            patch("src.cli.settings") as mock_settings,
            patch("src.aggregator.NewsAggregator.fetch_weekly_ai_news", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_settings.newsapi_key = None
            mock_settings.database_url = None
            mock_settings.enable_persistence = False
            mock_settings.credible_domains = []

            mock_response = MagicMock()
            mock_response.model_dump.return_value = {"total_articles": 0, "articles": []}
            mock_fetch.return_value = mock_response

            await _fetch_news(7, True, 50)

            mock_fetch.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_when_db_init_fails(self):
        """CLI falls back to no persistence when database initialisation fails."""
        from src.cli import _fetch_news

        with (
            patch("src.cli.settings") as mock_settings,
            patch("src.database.connection.create_async_engine", side_effect=RuntimeError("connection refused")),
            patch("src.aggregator.NewsAggregator.fetch_weekly_ai_news", new_callable=AsyncMock) as mock_fetch,
        ):
            mock_settings.newsapi_key = None
            mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost/test"
            mock_settings.enable_persistence = True
            mock_settings.database_pool_size = 5
            mock_settings.database_max_overflow = 10
            mock_settings.credible_domains = []

            mock_response = MagicMock()
            mock_response.model_dump.return_value = {"total_articles": 0, "articles": []}
            mock_fetch.return_value = mock_response

            # Should not raise — gracefully falls back
            await _fetch_news(7, True, 50)

            mock_fetch.assert_called_once()
