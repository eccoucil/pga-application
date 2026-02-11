"""Persistence layer for crawl results (Neo4j + Supabase).

Extracted from ``WebCrawlerAgent`` so storage logic can be tested and
replaced independently.
"""

import logging
from typing import Optional

from supabase import AsyncClient

from app.models.knowledge_graph import CompanyNode, DigitalAssetNode, DigitalAssetType
from app.models.web_crawler import (
    AttackSurfaceSummary,
    BusinessContext,
    CrawlRequest,
    DigitalAsset,
    GraphAsset,
    GraphCompany,
    OrganizationInfo,
)
from app.services.neo4j_service import Neo4jService

logger = logging.getLogger(__name__)

# System UUID indicates internal operation — skip user_id to avoid FK constraint
SYSTEM_USER_UUID = "00000000-0000-0000-0000-000000000000"


class StorageService:
    """Handles persistence of crawl results to Neo4j and Supabase."""

    def __init__(self, neo4j: Neo4jService, supabase: AsyncClient) -> None:
        self.neo4j = neo4j
        self.supabase = supabase

    # ------------------------------------------------------------------
    # Neo4j
    # ------------------------------------------------------------------

    async def store_in_neo4j(
        self,
        request: CrawlRequest,
        business_context: Optional[BusinessContext],
        assets: list[DigitalAsset],
    ) -> tuple[
        Optional[GraphCompany], list[GraphAsset], Optional[AttackSurfaceSummary]
    ]:
        """Persist company + assets to Neo4j and return graph representations.

        Returns:
            (graph_company, graph_assets, attack_surface)
        """
        if not business_context:
            return None, [], None

        company_node = CompanyNode(
            client_id=request.client_id,
            project_id=request.project_id,
            web_domain=request.web_domain,
            name=business_context.company_name,
            industry_type=business_context.industry,
            description=business_context.description,
        )
        company_node = await self.neo4j.create_company(company_node)

        graph_company = GraphCompany(
            id=company_node.id,
            name=company_node.name,
            domain=company_node.web_domain or request.web_domain,
            industry=company_node.industry_type,
            description=company_node.description,
            project_id=company_node.project_id,
        )

        graph_assets: list[GraphAsset] = []
        asset_type_counts: dict[str, int] = {}
        tech_stack: set[str] = set()

        for asset in assets:
            try:
                kg_type_map = {
                    "subdomain": DigitalAssetType.SUBDOMAIN,
                    "portal": DigitalAssetType.PORTAL,
                    "api": DigitalAssetType.API,
                    "application": DigitalAssetType.APPLICATION,
                    "website": DigitalAssetType.WEBSITE,
                }
                kg_type = kg_type_map.get(asset.asset_type, DigitalAssetType.WEBSITE)

                asset_node = DigitalAssetNode(
                    project_id=request.project_id,
                    organization_id=company_node.id or "",
                    url=asset.url,
                    asset_type=kg_type,
                    title=asset.description[:100] if asset.description else None,
                    description=asset.description,
                )
                asset_node = await self.neo4j.create_digital_asset(
                    asset_node, company_node.id or ""
                )

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

            except Exception as e:
                logger.warning(f"Failed to store asset {asset.url}: {e}")

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
