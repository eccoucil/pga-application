#!/usr/bin/env python
"""
Test script for QuestionGenerator with real Supabase/Neo4j data.

Usage: cd backend && uv run python scripts/test_question_generator.py

Tests ISO Clause 4 (Context of Organization) with Banking industry context.
"""

import asyncio
import sys
from datetime import datetime

from app.db.supabase import get_supabase_client
from app.services.question_generator import (
    ControlDefinition,
    get_question_generator,
    reset_question_generator,
)
from app.services.context_aggregator import (
    UnifiedContextProfile,
    OrganizationContext,
    DiscoveredContext,
    DigitalAssetContext,
    ExistingPolicies,
    RiskProfile,
    get_context_aggregator,
)


def fetch_iso_clause_controls(clause_number: int) -> list[dict]:
    """Fetch ISO organizational clause controls from Supabase."""
    supabase = get_supabase_client()
    result = (
        supabase.table("iso_requirements")
        .select("*")
        .eq("clause_type", "management")
        .like("identifier", f"{clause_number}.%")
        .order("identifier")
        .execute()
    )
    return result.data or []


def fetch_existing_client_project() -> tuple[str, str] | None:
    """Find an existing client and project from Supabase."""
    supabase = get_supabase_client()

    # Get first client
    clients = supabase.table("clients").select("id, name").limit(1).execute()
    if not clients.data:
        return None

    client_id = clients.data[0]["id"]
    client_name = clients.data[0]["name"]

    # Get first project for this client
    projects = (
        supabase.table("projects")
        .select("id, name")
        .eq("client_id", client_id)
        .limit(1)
        .execute()
    )
    if not projects.data:
        return None

    project_id = projects.data[0]["id"]
    project_name = projects.data[0]["name"]

    print(f"Found client: {client_name} ({client_id})")
    print(f"Found project: {project_name} ({project_id})")

    return client_id, project_id


async def build_context_from_neo4j(
    client_id: str, project_id: str
) -> UnifiedContextProfile | None:
    """Build context from Neo4j organization data."""
    try:
        aggregator = get_context_aggregator()
        context = await aggregator.build_context(
            client_id=client_id,
            project_id=project_id,
            section="4",  # Clause 4
            framework="iso_27001",
        )
        return context
    except Exception as e:
        print(f"Warning: Could not build context from Neo4j: {e}")
        return None


def build_fallback_banking_context(
    department: str = "Information Technology",
) -> UnifiedContextProfile:
    """
    Build a realistic Banking & Financial Services context for testing.

    Args:
        department: The department to generate questions for.
                   Supported: Human Resources, Information Technology, Finance, etc.
    """
    # Department-specific risk mappings
    dept_risks = {
        "Human Resources": [
            "Personnel data breach (PII, salary, performance records)",
            "Insider threat from disgruntled employees",
            "Onboarding/offboarding security gaps",
            "Unauthorized access to HR systems",
            "Background screening failures",
        ],
        "Information Technology": [
            "System vulnerabilities and misconfigurations",
            "Unauthorized access to production systems",
            "Source code exposure or theft",
            "API security weaknesses",
            "Cloud infrastructure mismanagement",
        ],
        "Finance": [
            "Financial fraud and embezzlement",
            "Audit trail manipulation",
            "Unauthorized transaction approvals",
            "Payment system vulnerabilities",
            "Financial reporting integrity",
        ],
    }

    dept_focus = {
        "Human Resources": {
            "primary_assets": [
                "employee personal records",
                "payroll and compensation data",
                "performance evaluations",
                "recruitment databases",
                "training records",
            ],
            "key_controls": [
                "access provisioning/deprovisioning",
                "background screening procedures",
                "security awareness training",
                "employment contract security clauses",
                "exit interview and offboarding",
            ],
            "evidence_types": [
                "access request and approval forms",
                "training completion records",
                "offboarding checklists",
                "background check reports",
                "security acknowledgment signatures",
            ],
        },
        "Information Technology": {
            "primary_assets": [
                "source code repositories",
                "production infrastructure",
                "APIs and integrations",
                "databases and data stores",
                "network infrastructure",
            ],
            "key_controls": [
                "change management procedures",
                "access control and authentication",
                "vulnerability management",
                "configuration management",
                "backup and recovery",
            ],
            "evidence_types": [
                "access logs and audit trails",
                "change request records",
                "vulnerability scan reports",
                "configuration baselines",
                "backup verification records",
            ],
        },
        "Finance": {
            "primary_assets": [
                "financial systems and ERP",
                "payment processing systems",
                "financial records and reports",
                "banking credentials",
                "audit documentation",
            ],
            "key_controls": [
                "segregation of duties",
                "transaction approval workflows",
                "financial system access controls",
                "audit trail maintenance",
                "reconciliation procedures",
            ],
            "evidence_types": [
                "approval matrices",
                "transaction logs",
                "reconciliation reports",
                "access review records",
                "audit findings and responses",
            ],
        },
    }

    # Get department-specific data or defaults
    department_risks = dept_risks.get(
        department, ["General departmental security risks"]
    )
    department_focus = dept_focus.get(department, None)

    return UnifiedContextProfile(
        organization=OrganizationContext(
            name="Apex Financial Services",
            industry_type="Banking & Financial Services",
            nature_of_business=(
                "Retail banking, corporate banking, wealth management, "
                "and digital payment services for Malaysian market"
            ),
            department=department,
            scope_statement_isms=(
                "ISMS covers all customer-facing digital banking systems, "
                "core banking infrastructure, payment processing, and "
                "customer data management across headquarters and 50 branches"
            ),
            web_domain="apexfinancial.com.my",
        ),
        discovered_context=DiscoveredContext(
            services=[
                "Retail Banking",
                "Corporate Banking",
                "Wealth Management",
                "Digital Payments",
            ],
            digital_assets=[
                DigitalAssetContext(
                    url="https://portal.apexfinancial.com.my",
                    asset_type="portal",
                    title="Customer Internet Banking Portal",
                    purpose="Online banking for retail customers",
                    technology_hints=["React", "Node.js", "AWS"],
                ),
                DigitalAssetContext(
                    url="https://api.apexfinancial.com.my",
                    asset_type="api",
                    title="Open Banking API Gateway",
                    purpose="Third-party integrations and fintech partners",
                    technology_hints=["Kong", "OAuth 2.0"],
                ),
                DigitalAssetContext(
                    url="https://mobile.apexfinancial.com.my",
                    asset_type="application",
                    title="Mobile Banking App Backend",
                    purpose="iOS and Android mobile banking services",
                ),
            ],
            technology_hints=[
                "AWS",
                "PostgreSQL",
                "Redis",
                "Kubernetes",
                "Elasticsearch",
            ],
            certifications=["ISO 27001:2022", "PCI DSS v4.0"],
            partnerships=["Visa", "Mastercard", "PayNet"],
        ),
        existing_policies=ExistingPolicies(
            controls_addressed=["A.5.1", "A.5.2", "A.6.1", "A.8.1"],
            policy_summaries=[],
        ),
        risk_profile=RiskProfile(
            industry_risks=[
                "Financial fraud and cyber attacks",
                "Customer data breach",
                "Regulatory non-compliance (BNM RMIT, PDPA)",
                "Business continuity disruption",
            ],
            department_risks=department_risks,
            department_focus=department_focus,
            asset_exposure="high",
            regulatory_pressure="high",
        ),
    )


def print_separator(char: str = "=", width: int = 70):
    print(char * width)


def print_question_details(question, show_grounding: bool = True):
    """Pretty print a generated question."""
    print(f"\n  Q{question.question_number} [{question.question_type}]")
    print(f"  {'-' * 60}")
    print(f"  {question.question_text}")
    print(f"\n  Expected Evidence: {', '.join(question.expected_evidence[:3])}")
    if question.confidence:
        conf = question.confidence
        print(
            f"  Confidence: {conf.overall:.2f} "
            f"(grounding={conf.grounding_score:.2f}, "
            f"context={conf.context_score:.2f}, "
            f"specificity={conf.specificity_score:.2f})"
        )
    if show_grounding:
        grounding = question.grounding_source[:100]
        if len(question.grounding_source) > 100:
            grounding += "..."
        print(f"  Grounding: {grounding}")


async def test_department_questions(
    generator,
    control: ControlDefinition,
    department: str,
):
    """Test question generation for a specific department."""
    print(f"\n{'#' * 70}")
    print(f"# DEPARTMENT: {department}")
    print(f"{'#' * 70}")

    context = build_fallback_banking_context(department=department)

    print(f"Organization: {context.organization.name}")
    print(f"Industry: {context.organization.industry_type}")
    print(f"Department: {context.organization.department}")

    # Show department-specific context
    if context.risk_profile.department_risks:
        print("\nDepartment Risks:")
        for risk in context.risk_profile.department_risks[:3]:
            print(f"  - {risk}")

    if context.risk_profile.department_focus:
        focus = context.risk_profile.department_focus
        print("\nDepartment Assets:")
        for asset in focus.get("primary_assets", [])[:3]:
            print(f"  - {asset}")
        print("\nDepartment Controls:")
        for ctrl in focus.get("key_controls", [])[:3]:
            print(f"  - {ctrl}")

    print(f"\n{'=' * 70}")
    print(f"CONTROL: {control.identifier} - {control.title}")
    print(f"{'=' * 70}")

    try:
        result = await generator.generate_for_control(
            control=control,
            context=context,
            skip_validation=False,
        )

        print(f"\nPersona Used: {result.persona_used}")
        print(f"Priority: {result.priority}")
        print(f"\nGenerated {len(result.questions)} questions:")

        for question in result.questions:
            print_question_details(question, show_grounding=False)

        # Verify department-specific content
        dept_mentions = sum(
            1
            for q in result.questions
            if department.lower() in q.question_text.lower()
            or any(
                asset.lower() in q.question_text.lower()
                for asset in (context.risk_profile.department_focus or {}).get(
                    "primary_assets", []
                )
            )
        )
        print(
            f"\n  Department-specific mentions: {dept_mentions}/{len(result.questions)} questions"
        )

    except Exception as e:
        print(f"ERROR generating questions: {e}")
        import traceback

        traceback.print_exc()


async def main():
    print_separator()
    print("QuestionGenerator Test - Department-Specific Question Generation")
    print_separator()
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Step 1: Fetch ISO controls
    print("Step 1: Fetching ISO Clause 4 controls from Supabase...")
    controls_data = fetch_iso_clause_controls(4)

    if not controls_data:
        print("ERROR: No ISO Clause 4 controls found in iso_requirements table!")
        print("Please ensure the iso_requirements table is populated.")
        sys.exit(1)

    print(f"Found {len(controls_data)} controls in Clause 4")

    # Use first control for department comparison
    control_data = controls_data[0]
    control = ControlDefinition(
        identifier=control_data["identifier"],
        title=control_data["title"],
        description=control_data.get("description"),
        category=control_data.get("category"),
        key_activities=control_data.get("key_activities", []),
    )

    print(f"\nUsing control: {control.identifier} - {control.title}")

    # Step 2: Generate questions for different departments
    print("\nStep 2: Testing department-specific question generation...")
    reset_question_generator()
    generator = get_question_generator()

    # Test with different departments to compare output
    test_departments = ["Human Resources", "Information Technology", "Finance"]

    for department in test_departments:
        await test_department_questions(generator, control, department)

    print_separator()
    print("SUMMARY: Department-Specific Question Generation Test")
    print_separator()
    print("""
Expected Observations:
1. HR questions should reference: employee records, payroll, training records
2. IT questions should reference: source code, APIs, production systems
3. Finance questions should reference: financial systems, transactions, audit trails

Each department's questions should be distinctly different, NOT generic.
    """)
    print(f"Test completed: {datetime.now().isoformat()}")
    print_separator()


if __name__ == "__main__":
    asyncio.run(main())
