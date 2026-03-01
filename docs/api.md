# AI News API Reference

Base URL: `https://<service-url>`

All date/time calculations use **Australia/Sydney** timezone.

---

## GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "ok",
  "database": "enabled"  // or "disabled"
}
```

---

## GET /api/v1/news/ai

Retrieve AI news articles published in the last N days.

Only includes articles whose **publication date** (not update date) falls within the window. Articles are deduplicated and marked for credibility before being returned.

### Parameters

| Parameter | Type | Default | Range | Description |
|---|---|---|---|---|
| `days` | int | 7 | 1-30 | Days to look back from now (Sydney time) |
| `credible_only` | bool | true | - | Only return articles from credible sources |
| `limit` | int | _(all)_ | 1-500 | Maximum articles to return. Omit to return all. |
| `max_results` | int | 100 | 1-500 | Maximum articles to fetch from each news source before filtering |
| `source` | string | live | `live` / `cached` | `live` fetches from news APIs; `cached` reads from database |

### Example

```
GET /api/v1/news/ai?days=3&credible_only=true&limit=10&max_results=200
```

### Response

```json
{
  "total_articles": 42,
  "query": "AI news (last week, Sydney time)",
  "from_date_sydney": "2026-02-23 00:00:00 AEDT",
  "to_date_sydney": "2026-03-02 14:30:00 AEDT",
  "sources_queried": ["newsapi", "google_rss"],
  "articles": [
    {
      "title": "OpenAI releases GPT-5",
      "description": "OpenAI announced the release of GPT-5...",
      "url": "https://openai.com/blog/gpt-5",
      "published_at": "2026-03-01T10:00:00+00:00",
      "published_at_sydney": "2026-03-01 21:00:00 AEDT",
      "source": {
        "name": "OpenAI",
        "url": "https://openai.com/blog/gpt-5",
        "is_credible": true
      },
      "image_url": "https://example.com/image.jpg",
      "fetched_from": "newsapi"
    }
  ]
}
```

### Notes

- `total_articles` equals the number of articles in the response (i.e. after all filtering and the `limit` cap).
- When `limit` is omitted, all matching articles are returned.
- `max_results` controls how many articles each source (Google RSS, NewsAPI) fetches. Increase this if `credible_only=true` returns fewer articles than expected.
- `source=cached` reads from the PostgreSQL database (faster, no external API calls). `source=live` fetches fresh data and persists to the database.

---

## GET /api/v1/news/slack

Same data as `/news/ai` but formatted as a **Slack Block Kit** JSON payload. The response can be POSTed directly to a Slack webhook or used in an n8n Slack node.

### Parameters

| Parameter | Type | Default | Range | Description |
|---|---|---|---|---|
| `days` | int | 7 | 1-30 | Days to look back from now (Sydney time) |
| `credible_only` | bool | true | - | Only return articles from credible sources |
| `limit` | int | _(all)_ | 1-500 | Maximum articles to return. Omit to return all. |
| `max_results` | int | 100 | 1-500 | Maximum articles to fetch from each news source before filtering |
| `source` | string | live | `live` / `cached` | `live` fetches from news APIs; `cached` reads from database |

### Example

```
GET /api/v1/news/slack?days=7&limit=5
```

### Response

```json
{
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": ":newspaper: AI News Digest -- 5 of 42 articles",
        "emoji": true
      }
    },
    {
      "type": "context",
      "elements": [
        {
          "type": "mrkdwn",
          "text": "*Period:* 2026-02-23 00:00:00 AEDT -- 2026-03-02 14:30:00 AEDT  |  Credible sources only"
        }
      ]
    },
    { "type": "divider" },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*<https://openai.com/blog/gpt-5|OpenAI releases GPT-5>*\n_OpenAI_ :white_check_mark:  |  2026-03-01 21:00:00 AEDT"
      }
    }
  ]
}
```

### Usage with n8n

```
HTTP Request node (GET /api/v1/news/slack) -> Slack node (Block Kit message)
```

---

## GET /api/v1/news/sources

List which news sources are configured and their availability. Also returns database statistics if persistence is enabled.

### Parameters

None.

### Example

```
GET /api/v1/news/sources
```

### Response

```json
{
  "sources": [
    { "name": "newsapi", "available": true },
    { "name": "google_rss", "available": true }
  ],
  "database_enabled": true,
  "database_stats": {
    "total_articles": 1250,
    "credible_articles": 830
  }
}
```

### Notes

- `newsapi` requires the `AINEWS_NEWSAPI_KEY` environment variable to be set.
- `google_rss` is always available (no API key required).
- `database_stats` is only present when `database_enabled` is `true`.
