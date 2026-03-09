from tests.conftest import make_article

from src.categories import Category, classify_article


class TestClassifyArticle:
    def test_gemini_in_title(self):
        article = make_article(title="Google Gemini Pro gets major update")
        assert classify_article(article) == Category.GEMINI_N8N

    def test_vertex_ai(self):
        article = make_article(title="Vertex AI adds new features for enterprise")
        assert classify_article(article) == Category.GEMINI_N8N

    def test_n8n(self):
        article = make_article(title="n8n releases version 2.0 with AI nodes")
        assert classify_article(article) == Category.GEMINI_N8N

    def test_security_ai_threat(self):
        article = make_article(title="New AI threat targets enterprise systems")
        assert classify_article(article) == Category.SECURITY_RISK

    def test_deepfake(self):
        article = make_article(title="Deepfake attacks increase by 300%")
        assert classify_article(article) == Category.SECURITY_RISK

    def test_prompt_injection(self):
        article = make_article(title="Prompt injection vulnerability found in LLM apps")
        assert classify_article(article) == Category.SECURITY_RISK

    def test_ai_safety(self):
        article = make_article(title="New AI safety research published by Anthropic")
        assert classify_article(article) == Category.SECURITY_RISK

    def test_productivity_slack(self):
        article = make_article(title="Slack integrates AI assistant features")
        assert classify_article(article) == Category.PRODUCTIVITY_TOOLS

    def test_productivity_notion(self):
        article = make_article(title="Notion AI gets major update for teams")
        assert classify_article(article) == Category.PRODUCTIVITY_TOOLS

    def test_github_copilot(self):
        article = make_article(title="GitHub Copilot now supports multi-file editing")
        assert classify_article(article) == Category.PRODUCTIVITY_TOOLS

    def test_product_launch_openai(self):
        article = make_article(title="OpenAI launches GPT-5 with new capabilities")
        assert classify_article(article) == Category.PRODUCT_LAUNCH

    def test_product_launch_anthropic(self):
        article = make_article(title="Anthropic announces Claude 4 model")
        assert classify_article(article) == Category.PRODUCT_LAUNCH

    def test_product_launch_meta(self):
        article = make_article(title="Meta releases Llama 4 open-source model")
        assert classify_article(article) == Category.PRODUCT_LAUNCH

    def test_business_partnership(self):
        article = make_article(title="Microsoft and Accenture forge AI partnership")
        assert classify_article(article) == Category.BUSINESS_ADOPTION

    def test_business_enterprise_deploy(self):
        article = make_article(title="Enterprise AI adoption surges in 2026")
        assert classify_article(article) == Category.BUSINESS_ADOPTION

    def test_industry_regulation(self):
        article = make_article(title="EU AI Act enforcement begins in March")
        assert classify_article(article) == Category.INDUSTRY_NEWS

    def test_industry_funding(self):
        article = make_article(title="AI startup raises Series C funding round")
        assert classify_article(article) == Category.INDUSTRY_NEWS

    def test_industry_open_source(self):
        article = make_article(
            title="Major open source LLM released to research community"
        )
        assert classify_article(article) == Category.INDUSTRY_NEWS

    def test_gemini_takes_priority_over_product_launch(self):
        """Gemini news should be categorized as GEMINI_N8N even if it's also a launch."""
        article = make_article(title="Google launches Gemini 2.0 model")
        assert classify_article(article) == Category.GEMINI_N8N

    def test_security_takes_priority_over_business(self):
        """Security news should be categorized as SECURITY_RISK over business."""
        article = make_article(
            title="AI security vulnerabilities found in enterprise deployment"
        )
        assert classify_article(article) == Category.SECURITY_RISK

    def test_unclassified_defaults_to_industry(self):
        """Articles that don't match any pattern default to INDUSTRY_NEWS."""
        article = make_article(
            title="An interesting article about technology",
            description="Some general tech news",
        )
        assert classify_article(article) == Category.INDUSTRY_NEWS

    def test_description_used_for_classification(self):
        """Classification should check description too, not just title."""
        article = make_article(
            title="Major update released",
            description="Google Gemini gets enterprise features",
        )
        assert classify_article(article) == Category.GEMINI_N8N
