from tests.conftest import make_article
from src.formatters.slack import format_article_block, format_articles_for_slack, _truncate


class TestTruncate:
    def test_short_text_unchanged(self):
        assert _truncate("hello", 10) == "hello"

    def test_long_text_truncated(self):
        result = _truncate("a" * 200, 50)
        assert len(result) == 50
        assert result.endswith("...")

    def test_exact_length_unchanged(self):
        text = "a" * 150
        assert _truncate(text, 150) == text


class TestFormatArticleBlock:
    def test_basic_structure(self, sample_article):
        blocks = format_article_block(sample_article)
        assert blocks[0]["type"] == "divider"
        assert blocks[1]["type"] == "section"

    def test_includes_title_link(self, sample_article):
        blocks = format_article_block(sample_article)
        text = blocks[1]["text"]["text"]
        assert sample_article.url in text
        assert sample_article.title in text

    def test_credible_badge_shown(self):
        article = make_article(is_credible=True)
        article.source.is_credible = True
        blocks = format_article_block(article)
        text = blocks[1]["text"]["text"]
        assert ":white_check_mark:" in text

    def test_no_badge_for_not_credible(self):
        article = make_article(is_credible=False)
        blocks = format_article_block(article)
        text = blocks[1]["text"]["text"]
        assert ":white_check_mark:" not in text

    def test_image_accessory_when_present(self):
        article = make_article(image_url="https://example.com/img.jpg")
        blocks = format_article_block(article)
        section = blocks[1]
        assert "accessory" in section
        assert section["accessory"]["type"] == "image"

    def test_no_image_accessory_when_absent(self, sample_article):
        blocks = format_article_block(sample_article)
        assert "accessory" not in blocks[1]

    def test_description_context_when_present(self, sample_article):
        blocks = format_article_block(sample_article)
        # divider + section + context = 3 blocks
        assert len(blocks) == 3
        assert blocks[2]["type"] == "context"

    def test_no_description_context_when_absent(self):
        article = make_article(description=None)
        blocks = format_article_block(article)
        assert len(blocks) == 2  # divider + section only


class TestFormatArticlesForSlack:
    def test_has_header(self, sample_articles):
        result = format_articles_for_slack(
            articles=sample_articles,
            from_date="2026-02-18",
            to_date="2026-02-25",
            total=3,
        )
        assert result["blocks"][0]["type"] == "header"

    def test_has_context_block(self, sample_articles):
        result = format_articles_for_slack(
            articles=sample_articles,
            from_date="2026-02-18",
            to_date="2026-02-25",
            total=3,
        )
        assert result["blocks"][1]["type"] == "context"

    def test_footer_when_more_articles(self, sample_articles):
        result = format_articles_for_slack(
            articles=sample_articles,
            from_date="2026-02-18",
            to_date="2026-02-25",
            total=100,
            limit=3,
        )
        blocks = result["blocks"]
        # Last block should be the "showing top N" footer
        assert "Showing top" in blocks[-1]["elements"][0]["text"]

    def test_no_footer_when_all_shown(self, sample_articles):
        result = format_articles_for_slack(
            articles=sample_articles,
            from_date="2026-02-18",
            to_date="2026-02-25",
            total=3,
            limit=10,
        )
        blocks = result["blocks"]
        # Last block should NOT be a footer context
        last = blocks[-1]
        if last["type"] == "context" and "elements" in last:
            assert "Showing top" not in last["elements"][0].get("text", "")

    def test_empty_articles(self):
        result = format_articles_for_slack(
            articles=[],
            from_date="2026-02-18",
            to_date="2026-02-25",
            total=0,
        )
        assert result["blocks"][0]["type"] == "header"
        assert "0 of 0" in result["blocks"][0]["text"]["text"]
