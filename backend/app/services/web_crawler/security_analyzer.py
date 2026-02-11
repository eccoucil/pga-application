"""Security analysis: HTTP headers, SSL, and LLM-based indicator extraction.

Combines pure-HTTP checks (fast, deterministic, zero tokens) with an
optional LLM pass for security-related content mentions.
"""

import logging
import ssl
import socket
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from app.models.web_crawler import (
    PageData,
    SecurityContext,
    SecurityHeadersResult,
    SSLResult,
)
from app.services.web_crawler.base_extractor import BaseLLMExtractor

logger = logging.getLogger(__name__)

_TIMEOUT = 10
_RECOMMENDED_HEADERS = [
    "Content-Security-Policy",
    "Strict-Transport-Security",
    "X-Frame-Options",
    "X-Content-Type-Options",
    "Referrer-Policy",
]


# =====================================================================
# Pure-HTTP analysis (no LLM, no tokens)
# =====================================================================


async def analyze_headers(domain: str) -> Optional[SecurityHeadersResult]:
    """Check HTTP security headers for *domain*."""
    url = f"https://{domain}" if not domain.startswith("http") else domain

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, follow_redirects=True) as client:
            resp = await client.head(url)
            headers = resp.headers

            present: list[str] = []
            missing: list[str] = []

            for header in _RECOMMENDED_HEADERS:
                if header.lower() in {k.lower() for k in headers.keys()}:
                    present.append(header)
                else:
                    missing.append(header)

            score = len(present) / len(_RECOMMENDED_HEADERS)

            return SecurityHeadersResult(
                has_csp="Content-Security-Policy" in present,
                has_hsts="Strict-Transport-Security" in present,
                has_x_frame_options="X-Frame-Options" in present,
                has_x_content_type="X-Content-Type-Options" in present,
                has_referrer_policy="Referrer-Policy" in present,
                headers_present=present,
                headers_missing=missing,
                score=score,
            )
    except Exception as e:
        logger.warning(f"Security header analysis failed for {domain}: {e}")
        return None


def check_ssl(domain: str) -> Optional[SSLResult]:
    """Check SSL/TLS certificate for *domain* (synchronous)."""
    hostname = domain.replace("https://", "").replace("http://", "").split("/")[0]

    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=_TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                if not cert:
                    return SSLResult(is_valid=False)

                # Parse expiry
                not_after = cert.get("notAfter", "")
                expires_dt = None
                days_until_expiry = None
                if not_after:
                    try:
                        expires_dt = datetime.strptime(
                            not_after, "%b %d %H:%M:%S %Y %Z"
                        )
                        days_until_expiry = (
                            expires_dt - datetime.now(timezone.utc).replace(tzinfo=None)
                        ).days
                    except ValueError:
                        pass

                # Extract issuer
                issuer_parts = cert.get("issuer", ())
                issuer = None
                for rdn in issuer_parts:
                    for attr_type, attr_value in rdn:
                        if attr_type == "organizationName":
                            issuer = attr_value
                            break

                return SSLResult(
                    is_valid=True,
                    issuer=issuer,
                    expires=not_after,
                    protocol_version=ssock.version(),
                    days_until_expiry=days_until_expiry,
                )
    except Exception as e:
        logger.warning(f"SSL check failed for {domain}: {e}")
        return SSLResult(is_valid=False)


# =====================================================================
# LLM-based security indicator extraction
# =====================================================================


class SecurityIndicatorExtractor(BaseLLMExtractor):
    """Extracts security-related mentions from page content via LLM."""

    SYSTEM_PROMPT = (
        "You are a cybersecurity analyst. Analyze the provided web page content "
        "and extract any mentions of security practices, certifications, compliance "
        "frameworks, or security-related features.\n\n"
        "Return a JSON array of strings, each being a security indicator found:\n"
        '["ISO 27001 certified", "SOC 2 Type II compliant", "Uses AES-256 encryption", ...]\n\n'
        "If no security indicators found, return: []\n"
        "Only include explicitly mentioned indicators. Do NOT infer or fabricate."
    )

    def _prepare_content(self, pages: list[PageData], **kwargs: Any) -> str:
        combined = "\n\n---PAGE BREAK---\n\n".join(
            f"URL: {p.url}\n\n{p.content[:5000]}" for p in pages[:5]
        )
        return f"Extract security indicators from:\n\n{combined}"

    def _parse_result(
        self, data: list, pages: list[PageData], **kwargs: Any
    ) -> list[str]:
        return [str(item) for item in data if item]

    def _empty_result(self) -> list:
        return []

    def _expect_array(self) -> bool:
        return True

    def _max_tokens(self) -> int:
        return 1500


# =====================================================================
# Combined analysis
# =====================================================================


async def analyze_security(
    domain: str,
    pages: list[PageData],
    indicator_extractor: Optional[SecurityIndicatorExtractor] = None,
) -> SecurityContext:
    """Run all security analyses and return a combined ``SecurityContext``.

    Args:
        domain: Target domain.
        pages: Crawled pages for LLM indicator extraction.
        indicator_extractor: Optional LLM extractor (skipped if ``None``).
    """
    headers_result = await analyze_headers(domain)
    ssl_result = check_ssl(domain)

    indicators: list[str] = []
    if indicator_extractor and pages:
        indicators = await indicator_extractor.extract(pages)

    from app.services.web_crawler.site_intelligence import fetch_robots_data

    robots_data = await fetch_robots_data(domain)

    return SecurityContext(
        headers=headers_result,
        ssl=ssl_result,
        security_indicators=indicators,
        robots_data=robots_data,
    )
