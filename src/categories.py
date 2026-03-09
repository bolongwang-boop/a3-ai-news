"""Article category classification for curated AI news digests.

Classifies articles into content categories based on keyword matching
against titles and descriptions. Categories mirror the UpGuard AI &
Automation Director's interests: product launches, business adoption,
productivity tools, industry news, security/risk, and Gemini/n8n.
"""

import re
from enum import Enum

from src.models import Article


class Category(str, Enum):
    PRODUCT_LAUNCH = "product_launch"
    BUSINESS_ADOPTION = "business_adoption"
    PRODUCTIVITY_TOOLS = "productivity_tools"
    INDUSTRY_NEWS = "industry_news"
    SECURITY_RISK = "security_risk"
    GEMINI_N8N = "gemini_n8n"


CATEGORY_LABELS: dict[Category, str] = {
    Category.PRODUCT_LAUNCH: "Major Product Launch",
    Category.BUSINESS_ADOPTION: "Business & Adoption",
    Category.PRODUCTIVITY_TOOLS: "Productivity Tools",
    Category.INDUSTRY_NEWS: "Industry News",
    Category.SECURITY_RISK: "Security & Risk",
    Category.GEMINI_N8N: "Gemini / n8n",
}

# How many articles to select per category in the curated top-10 digest.
# Total = 10.
CATEGORY_QUOTAS: dict[Category, int] = {
    Category.PRODUCT_LAUNCH: 2,
    Category.BUSINESS_ADOPTION: 2,
    Category.PRODUCTIVITY_TOOLS: 1,
    Category.INDUSTRY_NEWS: 2,
    Category.SECURITY_RISK: 1,
    Category.GEMINI_N8N: 2,
}

# Overflow priority: when a category has fewer articles than its quota,
# redistribute slots to these categories (in order of priority).
OVERFLOW_PRIORITY: list[Category] = [
    Category.PRODUCT_LAUNCH,
    Category.BUSINESS_ADOPTION,
    Category.INDUSTRY_NEWS,
    Category.SECURITY_RISK,
    Category.PRODUCTIVITY_TOOLS,
    Category.GEMINI_N8N,
]

# --- Keyword patterns per category (compiled regexes, case-insensitive) ---

_GEMINI_N8N_RE = re.compile(
    r"\b("
    r"Gemini|Google Gemini|Gemini Pro|Gemini Ultra|Gemini Flash|Gemini Nano"
    r"|Vertex AI|Google AI Studio"
    r"|n8n|n8n\.io"
    r")\b",
    re.IGNORECASE,
)

_SECURITY_RISK_RE = re.compile(
    r"\b("
    r"AI security|AI risk|AI threat|AI attack|AI vulnerability"
    r"|AI safety|AI alignment|AI harm"
    r"|deepfake|jailbreak|prompt injection|adversarial"
    r"|cybersecurity.{0,20}AI|AI.{0,20}cybersecurity"
    r"|AI.{0,20}fraud|AI.{0,20}phishing|AI.{0,20}malware"
    r"|AI.{0,20}exploit|AI.{0,20}breach"
    r"|responsible AI|AI ethics|AI bias"
    r"|AI.{0,20}surveillance|AI.{0,20}privacy"
    r")\b",
    re.IGNORECASE,
)

_PRODUCTIVITY_TOOLS_RE = re.compile(
    r"\b("
    r"Asana|Notion|Slack|Google Workspace|Microsoft 365|Microsoft Teams"
    r"|Trello|Monday\.com|ClickUp|Jira|Confluence|Linear"
    r"|Copilot.{0,15}(?:productivity|workspace|office|Word|Excel|PowerPoint)"
    r"|AI.{0,15}(?:productivity|workflow|assistant|workspace|automate)"
    r"|(?:productivity|workflow|workspace).{0,15}AI"
    r"|Zapier|Make\.com|Power Automate"
    r"|GitHub Copilot|Cursor|Windsurf|Codeium|Tabnine"
    r")\b",
    re.IGNORECASE,
)

_PRODUCT_LAUNCH_RE = re.compile(
    r"\b("
    r"(?:launch|release|unveil|introduce|announce|debut|reveal|roll.?out)"
    r".{0,30}"
    r"(?:model|AI|GPT|Claude|Llama|Gemini|Mistral|Grok|Sora|DALL-E|Midjourney)"
    r"|(?:GPT-\d|Claude \d|Llama \d|Gemini \d|o\d|o\d-\w+)"
    r"|(?:OpenAI|Anthropic|Google|Meta|Mistral|xAI|Stability AI|Cohere)"
    r".{0,20}(?:new|latest|next|launch|release|unveil|announce|model)"
    r"|new.{0,10}(?:AI model|language model|foundation model)"
    r")\b",
    re.IGNORECASE,
)

_BUSINESS_ADOPTION_RE = re.compile(
    r"\b("
    r"partnership|enterprise|deploy|adoption|contract|deal"
    r"|(?:billion|million).{0,15}(?:AI|invest|fund|deal|revenue)"
    r"|AI.{0,15}(?:partnership|enterprise|deploy|adoption|integration)"
    r"|(?:partnership|enterprise|deploy|adoption).{0,15}AI"
    r"|corporate.{0,15}AI|AI.{0,15}strategy"
    r"|AI.{0,15}(?:revenue|growth|market|valuation)"
    r"|IPO.{0,15}AI|AI.{0,15}IPO"
    r"|acquire|acquisition|merger"
    r")\b",
    re.IGNORECASE,
)

_INDUSTRY_NEWS_RE = re.compile(
    r"\b("
    r"regulation|regulatory|legislation|law|policy|govern"
    r"|(?:EU|US|UK|Congress|Senate|Parliament|White House).{0,20}AI"
    r"|AI.{0,20}(?:EU|US|UK|Congress|Senate|Parliament|White House)"
    r"|AI Act|executive order"
    r"|funding round|Series [A-F]|venture capital|VC.{0,10}AI"
    r"|AI.{0,15}(?:funding|investment|raise|valuation)"
    r"|antitrust.{0,15}AI|AI.{0,15}antitrust"
    r"|AI.{0,15}(?:ban|restrict|limit|probe|investigate)"
    r"|open.?source.{0,15}(?:AI|model|LLM)"
    r")\b",
    re.IGNORECASE,
)


def classify_article(article: Article) -> Category:
    """Classify an article into one content category.

    Priority order (most specific first):
    1. Gemini / n8n (highest — always relevant to UpGuard stack)
    2. Security / Risk
    3. Productivity Tools
    4. Product Launch
    5. Business & Adoption
    6. Industry News (catch-all for regulation, funding)
    """
    text = f"{article.title} {article.description or ''}"

    if _GEMINI_N8N_RE.search(text):
        return Category.GEMINI_N8N
    if _SECURITY_RISK_RE.search(text):
        return Category.SECURITY_RISK
    if _PRODUCTIVITY_TOOLS_RE.search(text):
        return Category.PRODUCTIVITY_TOOLS
    if _PRODUCT_LAUNCH_RE.search(text):
        return Category.PRODUCT_LAUNCH
    if _BUSINESS_ADOPTION_RE.search(text):
        return Category.BUSINESS_ADOPTION
    if _INDUSTRY_NEWS_RE.search(text):
        return Category.INDUSTRY_NEWS

    # Default: treat unclassified articles as industry news
    return Category.INDUSTRY_NEWS
