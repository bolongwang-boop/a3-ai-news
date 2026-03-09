"""Slack Block Kit formatter for AI news articles.

Produces JSON payloads that can be POSTed directly to a Slack webhook
or used in an n8n Slack node.
"""

from src.models import Article, DigestResponse


def _truncate(text: str, max_length: int = 150) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3].rstrip() + "..."


def format_article_block(article: Article) -> list[dict]:
    """Convert a single Article into Slack Block Kit blocks."""
    blocks: list[dict] = []

    # Divider before each article
    blocks.append({"type": "divider"})

    # Main section: title (linked) + metadata
    title_link = f"<{article.url}|{article.title}>"
    text = f"*{title_link}*\n_{article.source.name}_  |  {article.published_at_sydney}"

    section: dict = {
        "type": "section",
        "text": {"type": "mrkdwn", "text": text},
    }

    # Add thumbnail if available
    if article.image_url:
        section["accessory"] = {
            "type": "image",
            "image_url": article.image_url,
            "alt_text": article.title[:75],
        }

    blocks.append(section)

    # Description context (if available)
    if article.description:
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": _truncate(article.description, 200)},
                ],
            }
        )

    return blocks


def format_articles_for_slack(
    articles: list[Article],
    from_date: str,
    to_date: str,
    total: int,
    limit: int = 10,
) -> dict:
    """Convert a list of Articles into a Slack Block Kit message payload.

    Returns a dict with a "blocks" key -- ready to POST to a Slack webhook
    or use in an n8n Slack message node.
    """
    shown = articles[:limit]

    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":newspaper: AI News Digest -- {len(shown)} of {total} articles",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"*Period:* {from_date} -- {to_date}  |  Credible sources only",
                },
            ],
        },
    ]

    for article in shown:
        blocks.extend(format_article_block(article))

    # Footer
    if total > limit:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_Showing top {limit} of {total} articles. Query the API for the full list._",
                    },
                ],
            }
        )

    return {"blocks": blocks}


# --- Category emoji mapping for the digest ---
_CATEGORY_EMOJI: dict[str, str] = {
    "product_launch": ":rocket:",
    "business_adoption": ":briefcase:",
    "productivity_tools": ":hammer_and_wrench:",
    "industry_news": ":newspaper:",
    "security_risk": ":shield:",
    "gemini_n8n": ":gem:",
}


def format_digest_for_slack(digest: DigestResponse) -> dict:
    """Format a curated digest as Slack Block Kit JSON.

    No URLs are included — the digest is designed for quick summary consumption.
    Each item shows its rank, category label, title, source, and date.
    """
    blocks: list[dict] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f":star: Top {digest.total_items} AI & Automation News",
                "emoji": True,
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"*Period:* {digest.from_date_sydney} -- {digest.to_date_sydney}  |  "
                        f"Curated from credible sources"
                    ),
                },
            ],
        },
    ]

    current_category = None
    for item in digest.items:
        # Category header when category changes
        if item.category != current_category:
            current_category = item.category
            emoji = _CATEGORY_EMOJI.get(item.category, ":newspaper:")
            blocks.append({"type": "divider"})
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{emoji} *{item.category_label}*",
                    },
                }
            )

        # Article item (no URL)
        desc = ""
        if item.description:
            desc = f"\n>{_truncate(item.description, 180)}"

        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*{item.rank}. {item.title}*\n"
                        f"_{item.source_name}_  |  {item.published_at_sydney}"
                        f"{desc}"
                    ),
                },
            }
        )

    # Footer
    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Curated by AI News API  |  Credible sources only_",
                },
            ],
        }
    )

    return {"blocks": blocks}
