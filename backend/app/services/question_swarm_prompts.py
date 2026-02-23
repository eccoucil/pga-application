"""Prompt building for the question generation swarm.

PROMPT CACHING STRATEGY:
1. Shared context (org info, criteria, JSON schema) — cached across workers
   - Worker 1: full input cost
   - Workers 2-6: 90% token discount (cache hits)

2. Per-worker controls section — NOT cached (unique to each worker)
   - Each worker gets 15-20 controls to generate questions for

PROMPT DESIGN:
- Senior GRC professional persona (20+ years audit experience)
- Five question styles: scenario-based, evidence-probing, implementation-depth,
  failure-mode, and effectiveness
- 45-word question limit (professional phrasing needs room)
- Maturity-tiered guidance (first-time → recurring → mature ISMS)
- Industry-appropriate GRC terminology encouraged
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
            "Organization is establishing its ISMS. Probe governance foundations: "
            "risk ownership and accountability structures, policy approval chains, "
            "asset inventory completeness, and initial risk assessment methodology. "
            "Ask how controls were selected and what gaps were identified during scoping. "
            "Still use professional tone — avoid simplistic 'do you have' questions."
        ),
        "recurring_assessment": (
            "Organization has an established ISMS. Probe operational effectiveness: "
            "control testing evidence and exception handling, incident response "
            "lessons learned, metrics-driven validation of control performance, "
            "management review outputs, and corrective action closure rates. "
            "Ask for trend data and root cause analysis."
        ),
        "mature_isms": (
            "Organization has a mature ISMS. Probe optimization and strategic integration: "
            "benchmarking against industry peers, automation ROI on compliance processes, "
            "threat-informed defense prioritization, integration with enterprise risk "
            "management and business continuity, board-level risk reporting, and "
            "how the ISMS drives competitive advantage."
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
            f"More detailed questions for: {', '.join(priority_domains)}."
        )

    concerns_section = ""
    if compliance_concerns:
        concerns_section = (
            f"\n\n## Compliance Concerns\n"
            f"Address these gaps: {compliance_concerns}"
        )

    skip_section = ""
    if controls_to_skip:
        skip_section = (
            f"\n\n## De-emphasized Controls\n"
            f"1 basic question for: {controls_to_skip}."
        )

    return f"""You are a senior GRC professional with 20+ years of audit experience across regulated industries. You write questions that probe implementation depth, demand evidence of real practice, and expose gaps that checklist audits miss. You use precise domain terminology naturally.

Organization: {org_name} ({industry})
Maturity: {maturity_level.replace('_', ' ').title()}
Depth: {q_count}

## Question Craft — Professional Audit Technique
1. MAX 45 WORDS per question — concise but substantive
2. ONE sentence, ONE control aspect per question — never combine topics
3. Use precise GRC terminology ({industry}-appropriate where possible)
4. Specific to {org_name} where possible

## Question Styles (vary across these)
- **Scenario-based**: "Walk me through...", "Describe what happens when...", "How did your last..."
- **Evidence-probing**: "What evidence demonstrates...", "Show me how you validate...", "What artifacts confirm..."
- **Implementation-depth**: "How do you reconcile...", "What is the handoff between...", "How does [X] integrate with..."
- **Failure-mode**: "When was the last time [control] failed, and how was it escalated?", "What happens if..."
- **Effectiveness**: "How do you measure whether...", "What metrics indicate...", "What was the trend in..."

## Examples

GOOD (senior GRC voice):
Control: "Access Control Policy"
✓ "Walk me through how a contractor's access is provisioned on day one and fully revoked upon engagement termination." → evidence: "Provisioning workflow, offboarding logs"
✓ "How do you reconcile access entitlements across HR systems, IAM platforms, and downstream applications during role transfers?" → evidence: "Reconciliation reports, IAM logs"
✓ "What was the exception rate in your last access certification cycle, and how were exceptions resolved?" → evidence: "Certification results, exception tracker"

BAD (junior checklist — avoid these patterns):
✗ "Do you have a documented access control policy?" (existence check — no depth)
✗ "Are access reviews conducted regularly?" (vague, yes/no)
✗ "Is there a process for revoking access?" (binary, no implementation detail)

Guidance: {maturity_guidance}{priority_section}{concerns_section}{skip_section}

## JSON Output (ONLY this format)
[
  {{
    "control_id": "ID",
    "control_title": "Title",
    "framework": "Framework Name",
    "questions": [
      {{
        "id": "q-<unique-id>",
        "question": "Professional audit question under 45 words",
        "category": "policy_existence|implementation|monitoring|effectiveness|documentation",
        "priority": "high|medium|low",
        "expected_evidence": "2-6 word evidence tag, e.g. Reconciliation reports, Incident post-mortems, Board risk minutes"
      }}
    ]
  }}
]"""


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
