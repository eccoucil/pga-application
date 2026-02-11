"""Named constants for the web crawler package.

Centralizes all magic numbers so they can be tuned from one place.
"""

# ---------------------------------------------------------------------------
# Content limits (characters)
# ---------------------------------------------------------------------------
MAX_CONTENT_LENGTH = 50_000  # Maximum stored content per page
BUSINESS_CONTENT_LIMIT = 10_000  # Per-page truncation for business analysis
ASSET_CONTENT_LIMIT = 5_000  # Per-page truncation for asset discovery
ORG_CONTENT_LIMIT = 8_000  # Per-page truncation for org info extraction

# ---------------------------------------------------------------------------
# Page / link limits
# ---------------------------------------------------------------------------
MAX_ANALYSIS_PAGES = 5  # Max pages sent to a single LLM extractor
MAX_ASSET_PAGES = 3  # Max pages for asset content analysis
MAX_LINKS_PER_PAGE = 100  # Links retained per page after extraction
MAX_DOMAIN_LINKS = 50  # Domain links sent to asset discovery

# ---------------------------------------------------------------------------
# Crawl behaviour
# ---------------------------------------------------------------------------
PAGE_TIMEOUT_SECONDS = 30  # Timeout per individual page fetch
WORD_COUNT_THRESHOLD = 50  # Minimum words for a page to be kept
CONCURRENT_CRAWL_LIMIT = 3  # Max pages fetched concurrently
CRAWL_RATE_LIMIT_PER_SEC = 2.0  # Max requests per second to target domain

# ---------------------------------------------------------------------------
# LLM limits
# ---------------------------------------------------------------------------
BUSINESS_MAX_TOKENS = 2_000
ASSET_MAX_TOKENS = 3_000
ORG_MAX_TOKENS = 2_000

# ---------------------------------------------------------------------------
# Confidence scoring weights (must sum to 1.0)
# ---------------------------------------------------------------------------
CONFIDENCE_WEIGHT_SOURCE_COUNT = 0.3
CONFIDENCE_WEIGHT_TEXT_CLARITY = 0.2
CONFIDENCE_WEIGHT_CROSS_VALIDATION = 0.3
CONFIDENCE_WEIGHT_GROUNDING = 0.2

# ---------------------------------------------------------------------------
# Confidence score normalisation caps
# ---------------------------------------------------------------------------
MAX_SOURCE_COUNT_PAGES = 10  # Score = 1.0 at this many pages
MAX_AVG_WORD_COUNT = 500  # Score = 1.0 at this average word count

# ---------------------------------------------------------------------------
# Asset type mapping (string → canonical string)
# ---------------------------------------------------------------------------
ASSET_TYPE_MAP: dict[str, str] = {
    "subdomain": "subdomain",
    "portal": "portal",
    "api": "api",
    "application": "application",
    "website": "website",
}
DEFAULT_ASSET_TYPE = "website"
