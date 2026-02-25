import json
from unittest.mock import AsyncMock, patch

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
