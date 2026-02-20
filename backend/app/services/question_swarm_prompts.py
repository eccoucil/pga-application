"""Prompt building for the question generation swarm.

Splits the system prompt into two parts for Anthropic prompt caching:
1. Shared context (org info, criteria, JSON schema) — cached across workers
2. Per-worker controls section — unique to each worker
"""


def build_shared_context(
    context: dict,
    *,
    maturity_level: str,
    question_depth: str,
    priority_domains: list[str] | None = None,
    compliance_concerns: str | None = None,
    controls_to_skip: str | None = None,
    questions_per_control: int | None = None,
) -> str:
    """Build the cacheable shared context portion of the system prompt.

    This part is identical across all workers and benefits from Anthropic's
    prompt caching (90% input token discount on cache hits).
    """
    org_name = context.get("organization_name", "the organization")
    industry = context.get("industry", "unspecified")

    # Question count from explicit choice or depth mapping
    if questions_per_control:
        q_count = f"{questions_per_control} questions per control"
    else:
        depth_map = {
            "high_level_overview": "2 questions per control",
            "balanced": "3 questions per control",
            "detailed_technical": "4-5 questions per control",
        }
        q_count = depth_map.get(question_depth, "3 questions per control")

    # Maturity complexity guidance
    maturity_map = {
        "first_time_audit": (
            "Focus on policy existence, basic documentation, and foundational "
            "controls. Use straightforward language. Prioritize 'do you have' "
            "over 'how effective is' questions."
        ),
        "recurring_assessment": (
            "Focus on implementation effectiveness, monitoring, and evidence "
            "of ongoing compliance. Ask about metrics, review cycles, and "
            "continuous improvement."
        ),
        "mature_isms": (
            "Focus on advanced effectiveness, optimization, and continuous "
            "improvement. Ask about benchmarking, automation, integration "
            "with business processes, and proactive threat management."
        ),
    }
    maturity_guidance = maturity_map.get(
        maturity_level, maturity_map["recurring_assessment"]
    )

    # Optional sections
    priority_section = ""
    if priority_domains:
        priority_section = (
            f"\n\n## Priority Focus Areas\n"
            f"Generate MORE detailed and in-depth questions for these domains: "
            f"{', '.join(priority_domains)}. "
            f"For other domains, still generate questions but at standard depth."
        )

    concerns_section = ""
    if compliance_concerns:
        concerns_section = (
            f"\n\n## Specific Compliance Concerns\n"
            f"The organization has flagged these concerns: {compliance_concerns}\n"
            f"Incorporate targeted questions that address these specific gaps "
            f"within relevant controls."
        )

    skip_section = ""
    if controls_to_skip:
        skip_section = (
            f"\n\n## Controls to De-emphasize\n"
            f"Reduce coverage for: {controls_to_skip}. "
            f"Generate only 1 basic question for these controls."
        )

    return f"""You are a Senior ISMS Compliance Consultant & Auditor.
Organization: {org_name} ({industry})

## Assessment Criteria
Maturity Level: {maturity_level.replace('_', ' ').title()}
Question Depth: {q_count}
Complexity Guidance: {maturity_guidance}{priority_section}{concerns_section}{skip_section}

## Instructions
Generate questions for the specific controls listed below. Output ONLY a JSON array with this schema:
[
  {{
    "control_id": "ID",
    "control_title": "Title",
    "framework": "Framework Name",
    "questions": [
      {{
        "id": "q-<unique-id>",
        "question": "The question text",
        "category": "policy_existence|implementation|monitoring|effectiveness|documentation",
        "priority": "high|medium|low",
        "expected_evidence": "Expected evidence",
        "guidance_notes": "Guidance notes"
      }}
    ]
  }}
]

Ensure questions are specific to {org_name}'s context."""


def build_controls_section(batch_controls_text: str) -> str:
    """Build the per-worker controls portion of the system prompt.

    This is unique to each worker and NOT cached.
    """
    return f"""## Controls to Process
{batch_controls_text}"""


def format_batch_controls(batch: list[dict]) -> str:
    """Format a batch of controls into text for the system prompt."""
    lines: list[str] = []
    for c in batch:
        section_ctx = f" ({c['section_title']})" if c.get("section_title") else ""
        lines.append(
            f"- **{c['id']}** [{c['framework']}]{section_ctx}: {c['title']} — {c['desc']}"
        )
    return "\n".join(lines)
