"""Persistence layer for crawl results (Supabase).

Extracted from ``WebCrawlerAgent`` so storage logic can be tested and
replaced independently.
"""

import logging
import uuid
from typing import Optional

from supabase import AsyncClient

from app.models.web_crawler import (
    AttackSurfaceSummary,
    BusinessContext,
    CrawlRequest,
    DigitalAsset,
    GraphAsset,
    GraphCompany,
    OrganizationInfo,
)

logger = logging.getLogger(__name__)

# System UUID indicates internal operation — skip user_id to avoid FK constraint
SYSTEM_USER_UUID = "00000000-0000-0000-0000-000000000000"


class StorageService:
    """Handles persistence of crawl results to Supabase."""

    def __init__(self, supabase: AsyncClient) -> None:
        self.supabase = supabase

    # ------------------------------------------------------------------
    # Graph representations (built in-memory, no external DB needed)
    # ------------------------------------------------------------------

    async def store_in_neo4j(
        self,
        request: CrawlRequest,
        business_context: Optional[BusinessContext],
        assets: list[DigitalAsset],
    ) -> tuple[
        Optional[GraphCompany], list[GraphAsset], Optional[AttackSurfaceSummary]
    ]:
        """Build graph representations from crawl data (no Neo4j).

        Returns:
            (graph_company, graph_assets, attack_surface)
        """
        if not business_context:
            return None, [], None

        graph_company = GraphCompany(
            id=str(uuid.uuid4()),
            name=business_context.company_name,
            domain=request.web_domain,
            industry=business_context.industry,
            description=business_context.description,
            project_id=request.project_id,
        )

        graph_assets: list[GraphAsset] = []
        asset_type_counts: dict[str, int] = {}
        tech_stack: set[str] = set()

        for asset in assets:
            graph_assets.append(
                GraphAsset(
                    url=asset.url,
                    asset_type=asset.asset_type,
                    description=asset.description,
                    purpose=asset.purpose,
                    technology_hints=asset.technology_hints,
                )
            )
            asset_type_counts[asset.asset_type] = (
                asset_type_counts.get(asset.asset_type, 0) + 1
            )
            tech_stack.update(asset.technology_hints)

        attack_surface = AttackSurfaceSummary(
            total_assets=len(assets),
            asset_types=asset_type_counts,
            technology_stack=list(tech_stack),
        )

        return graph_company, graph_assets, attack_surface

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------

    async def store_in_supabase(
        self,
        request: CrawlRequest,
        user_id: str,
        pages_crawled: int,
        business_context: Optional[BusinessContext],
        assets: list[DigitalAsset],
        org_info: Optional[OrganizationInfo],
        confidence_score: float,
    ) -> None:
        """Persist crawl result row to the ``web_crawl_results`` table."""
        data: dict = {
            "client_id": request.client_id,
            "project_id": request.project_id,
            "web_domain": request.web_domain,
            "pages_crawled": pages_crawled,
            "business_context": business_context.model_dump()
            if business_context
            else None,
            "digital_assets": [a.model_dump() for a in assets],
            "organization_info": org_info.model_dump() if org_info else None,
            "confidence_score": confidence_score,
        }

        # Only include user_id if it's a real user (not system operation)
        if user_id != SYSTEM_USER_UUID:
            data["user_id"] = user_id

        await self.supabase.table("web_crawl_results").insert(data).execute()
