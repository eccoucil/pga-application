"""Framework router for ISO 27001 and BNM RMIT sections."""

import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user
from app.config import get_settings

router = APIRouter(prefix="/framework", tags=["framework"])


class ControlSummary(BaseModel):
    """Summary of a control for listing."""

    identifier: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = None


class SectionSummary(BaseModel):
    """Summary of a framework section."""

    section_id: str
    section_title: str
    control_count: int
    controls: list[ControlSummary] = Field(default_factory=list)


class FrameworkSections(BaseModel):
    """List of sections for a framework."""

    framework: str
    total_controls: int
    sections: list[SectionSummary]


# ISO 27001:2022 section mappings
ISO_27001_SECTIONS = {
    "management": {
        "4": "Context of the Organization",
        "5": "Leadership",
        "6": "Planning",
        "7": "Support",
        "8": "Operation",
        "9": "Performance Evaluation",
        "10": "Improvement",
    },
    "annex_a": {
        "A.5": "Organizational Controls",
        "A.6": "People Controls",
        "A.7": "Physical Controls",
        "A.8": "Technological Controls",
    },
}

# BNM RMIT section mappings
BNM_RMIT_SECTIONS = {
    "8": "Governance",
    "9": "Risk Management",
    "10": "Technology Operations Management",
    "11": "Cybersecurity Management",
    "12": "Technology Audit",
    "13": "Internal Audit",
    "14": "Cloud Services",
}


@router.get("/iso27001/sections", response_model=FrameworkSections)
async def get_iso27001_sections(
    include_controls: bool = Query(
        False, description="Include control details in response"
    ),
    current_user: dict = Depends(get_current_user),
) -> FrameworkSections:
    """
    Get ISO 27001:2022 sections with optional control details.

    Returns both management clauses (4-10) and Annex A controls (A.5-A.8).
    """
    settings = get_settings()

    # Query from Supabase
    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    # Get all ISO requirements
    result = supabase.table("iso_requirements").select("*").execute()
    requirements = result.data

    # Group by section
    sections = []
    total_controls = 0

    # Process management clauses
    for clause_id, clause_title in ISO_27001_SECTIONS["management"].items():
        clause_controls = [
            r
            for r in requirements
            if r["clause_type"] == "management"
            and r["identifier"].startswith(clause_id)
        ]
        total_controls += len(clause_controls)

        section = SectionSummary(
            section_id=clause_id,
            section_title=clause_title,
            control_count=len(clause_controls),
        )

        if include_controls:
            section.controls = [
                ControlSummary(
                    identifier=c["identifier"],
                    title=c["title"],
                    description=c.get("description"),
                    category="Management",
                )
                for c in clause_controls
            ]

        sections.append(section)

    # Process Annex A sections
    for annex_id, annex_title in ISO_27001_SECTIONS["annex_a"].items():
        annex_controls = [
            r
            for r in requirements
            if r["clause_type"] == "domain" and r.get("category_code") == annex_id
        ]
        total_controls += len(annex_controls)

        section = SectionSummary(
            section_id=annex_id,
            section_title=annex_title,
            control_count=len(annex_controls),
        )

        if include_controls:
            section.controls = [
                ControlSummary(
                    identifier=c["identifier"],
                    title=c["title"],
                    description=c.get("description"),
                    category=c.get("category"),
                )
                for c in annex_controls
            ]

        sections.append(section)

    return FrameworkSections(
        framework="ISO 27001:2022",
        total_controls=total_controls,
        sections=sections,
    )


@router.get("/bnm_rmit/sections", response_model=FrameworkSections)
async def get_bnm_rmit_sections(
    include_controls: bool = Query(
        False, description="Include control details in response"
    ),
    current_user: dict = Depends(get_current_user),
) -> FrameworkSections:
    """
    Get BNM RMIT sections with optional control details.

    Returns sections 8-14 with their requirements.
    """
    settings = get_settings()

    # Query from Supabase
    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    # Get all BNM RMIT requirements
    result = supabase.table("bnm_rmit_requirements").select("*").execute()
    requirements = result.data

    # Group by section
    sections = []
    total_controls = 0

    for section_num, section_title in BNM_RMIT_SECTIONS.items():
        section_controls = [
            r for r in requirements if str(r.get("section_number")) == section_num
        ]
        total_controls += len(section_controls)

        section = SectionSummary(
            section_id=f"section_{section_num}",
            section_title=section_title,
            control_count=len(section_controls),
        )

        if include_controls:
            section.controls = [
                ControlSummary(
                    identifier=c["reference_id"],
                    title=c.get("subsection_title") or c["section_title"],
                    description=c.get("requirement_text"),
                    category=c.get("requirement_type"),
                )
                for c in section_controls
            ]

        sections.append(section)

    return FrameworkSections(
        framework="BNM RMIT",
        total_controls=total_controls,
        sections=sections,
    )


@router.get("/iso27001/section/{section_id}", response_model=SectionSummary)
async def get_iso27001_section_details(
    section_id: str,
    current_user: dict = Depends(get_current_user),
) -> SectionSummary:
    """
    Get detailed controls for a specific ISO 27001 section.

    Args:
        section_id: Section identifier (e.g., "A.5", "6")
    """
    if not re.match(r"^A\.\d{1,2}$|^\d{1,2}$", section_id):
        raise HTTPException(
            status_code=400, detail="Invalid section identifier format"
        )

    settings = get_settings()

    from supabase import create_client

    supabase = create_client(settings.supabase_url, settings.supabase_service_key)

    # Determine if management clause or Annex A
    if section_id.startswith("A."):
        # Annex A control
        result = (
            supabase.table("iso_requirements")
            .select("*")
            .eq("category_code", section_id)
            .execute()
        )
        section_title = ISO_27001_SECTIONS["annex_a"].get(
            section_id, f"Section {section_id}"
        )
    else:
        # Management clause
        result = (
            supabase.table("iso_requirements")
            .select("*")
            .eq("clause_type", "management")
            .like("identifier", f"{section_id}%")
            .execute()
        )
        section_title = ISO_27001_SECTIONS["management"].get(
            section_id, f"Clause {section_id}"
        )

    requirements = result.data

    if not requirements:
        raise HTTPException(status_code=404, detail=f"Section {section_id} not found")

    return SectionSummary(
        section_id=section_id,
        section_title=section_title,
        control_count=len(requirements),
        controls=[
            ControlSummary(
                identifier=c["identifier"],
                title=c["title"],
                description=c.get("description"),
                category=c.get("category") or "Management",
            )
            for c in requirements
        ],
    )
