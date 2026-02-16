from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    newsapi_key: str | None = None

    timezone: str = "Australia/Sydney"
    default_days_back: int = 7
    cache_ttl_minutes: int = 30

    credible_domains: list[str] = [
        # Wire services
        "reuters.com",
        "apnews.com",
        # Major news outlets
        "bbc.com",
        "bbc.co.uk",
        "theguardian.com",
        "nytimes.com",
        "washingtonpost.com",
        "abc.net.au",
        "sbs.com.au",
        "smh.com.au",
        # Tech publications
        "techcrunch.com",
        "wired.com",
        "arstechnica.com",
        "theverge.com",
        "technologyreview.com",
        "venturebeat.com",
        "zdnet.com",
        "cnet.com",
        "engadget.com",
        "tomsguide.com",
        # Science / academic
        "nature.com",
        "science.org",
        "ieee.org",
        "acm.org",
        "scientificamerican.com",
        # Business / financial
        "bloomberg.com",
        "ft.com",
        "cnbc.com",
        "businessinsider.com",
        "forbes.com",
    ]

    model_config = {"env_file": ".env", "env_prefix": "AINEWS_"}


settings = Settings()
