"""CLI entry point for fetching AI news and outputting as JSON.

Usage:
    python -m src.cli [--days N] [--credible-only] [--limit N]

If the environment variable AINEWS_OUTPUT_FILE is set, the JSON output
is written to that file path instead of stdout.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

import httpx

from src.aggregator import NewsAggregator
from src.config import settings
from src.sources.google_rss import GoogleRSSSource
from src.sources.newsapi import NewsAPISource

logger = logging.getLogger(__name__)


async def _fetch_news(days: int, credible_only: bool, limit: int) -> dict:
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        sources = [
            NewsAPISource(api_key=settings.newsapi_key, http_client=http_client),
            GoogleRSSSource(http_client=http_client),
        ]
        aggregator = NewsAggregator(
            sources=sources, settings=settings, repository=None
        )
        response = await aggregator.fetch_weekly_ai_news(
            days_back=days, credible_only=credible_only, limit=limit
        )
    return response.model_dump(mode="json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch latest AI news as JSON")
    parser.add_argument(
        "--days", type=int, default=settings.default_days_back,
        help=f"Days to look back (default: {settings.default_days_back})",
    )
    parser.add_argument(
        "--credible-only", action="store_true", default=True,
        help="Only return articles from credible sources (default: true)",
    )
    parser.add_argument(
        "--all-sources", action="store_true", default=False,
        help="Include articles from all sources, not just credible ones",
    )
    parser.add_argument(
        "--limit", type=int, default=50,
        help="Maximum number of articles to return (default: 50)",
    )
    args = parser.parse_args()

    credible_only = not args.all_sources

    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    try:
        data = asyncio.run(_fetch_news(args.days, credible_only, args.limit))
    except KeyboardInterrupt:
        sys.exit(130)

    output = json.dumps(data, indent=2, ensure_ascii=False)

    output_file = settings.output_file
    if output_file:
        path = Path(output_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(output, encoding="utf-8")
        print(f"Written {data['total_articles']} articles to {path}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
