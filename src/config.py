from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    newsapi_key: str | None = None

    timezone: str = "Australia/Sydney"
    default_days_back: int = 7
    cache_ttl_minutes: int = 30

    # CLI output
    output_file: str | None = None

    # Database
    database_url: str | None = None
    enable_persistence: bool = False
    database_pool_size: int = 5
    database_max_overflow: int = 10
    retention_days: int = 30

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
        "cio.com",
        "eweek.com",
        "infoworld.com",
        "computerworld.com",
        "csoonline.com",
        "networkworld.com",
        "towardsdatascience.com",
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
        "fortune.com",
        "hbr.org",
        "vox.com",
        "observer.com",
        # AI companies / cloud providers
        "openai.com",
        "deepmind.google",
        "anthropic.com",
        "arxiv.org",
        "huggingface.co",
        "aws.amazon.com",
        "cloud.google.com",
        "azure.microsoft.com",
    ]

    model_config = {"env_file": ".env", "env_prefix": "AINEWS_"}


settings = Settings()
