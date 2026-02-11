"""Framework documentation router — serves ISO 27001:2022 controls from markdown files."""

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/framework-docs", tags=["framework-docs"])

DOCS_DIR = Path(__file__).resolve().parents[3] / "docs" / "framework"
ANNEX_A_PATH = DOCS_DIR / "iso27001-2022-annex-a-controls.md"
MGMT_CLAUSES_PATH = DOCS_DIR / "iso27001-2022-management-clauses.md"


# ---------- Response models ----------


class AnnexAControl(BaseModel):
    control_id: str
    title: str
    description: str


class AnnexASection(BaseModel):
    section_id: str
    title: str
    control_count: int
    controls: list[AnnexAControl]


class AnnexAResponse(BaseModel):
    sections: list[AnnexASection]


class SubClause(BaseModel):
    sub_clause_id: str
    title: str
    content: str


class ManagementClause(BaseModel):
    clause_id: str
    title: str
    sub_clauses: list[SubClause]


class ManagementClausesResponse(BaseModel):
    clauses: list[ManagementClause]


class UpdateControlBody(BaseModel):
    title: str
    description: str


class UpdateClauseBody(BaseModel):
    content: str


# ---------- Annex A parsing ----------

_SECTION_RE = re.compile(r"^## (\d+)\.\s+(.+?)(?:\s*\(\d+ controls?\))?\s*$")
_ROW_RE = re.compile(r"^\|\s*(\d+\.\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$")


def _parse_annex_a(text: str) -> list[AnnexASection]:
    sections: list[AnnexASection] = []
    current: AnnexASection | None = None

    for line in text.splitlines():
        sec_match = _SECTION_RE.match(line)
        if sec_match:
            if current:
                current.control_count = len(current.controls)
                sections.append(current)
            current = AnnexASection(
                section_id=sec_match.group(1),
                title=sec_match.group(2).strip(),
                control_count=0,
                controls=[],
            )
            continue

        if current is None:
            continue

        row_match = _ROW_RE.match(line)
        if row_match:
            cid, title, desc = row_match.group(1), row_match.group(2).strip(), row_match.group(3).strip()
            # Skip header separator rows
            if cid.replace("-", "").replace(" ", "") == "":
                continue
            current.controls.append(AnnexAControl(control_id=cid, title=title, description=desc))

    if current:
        current.control_count = len(current.controls)
        sections.append(current)

    return sections


@router.get("/annex-a", response_model=AnnexAResponse)
async def get_annex_a():
    """Return all Annex A controls parsed from the markdown reference file."""
    if not ANNEX_A_PATH.exists():
        raise HTTPException(status_code=404, detail="Annex A markdown file not found")
    text = ANNEX_A_PATH.read_text(encoding="utf-8")
    return AnnexAResponse(sections=_parse_annex_a(text))


@router.put("/annex-a/{control_id}")
async def update_annex_a_control(control_id: str, body: UpdateControlBody):
    """Update a single Annex A control's title and description in the markdown file."""
    if not ANNEX_A_PATH.exists():
        raise HTTPException(status_code=404, detail="Annex A markdown file not found")

    text = ANNEX_A_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()
    found = False

    for i, line in enumerate(lines):
        row_match = _ROW_RE.match(line)
        if row_match and row_match.group(1) == control_id:
            lines[i] = f"| {control_id} | {body.title} | {body.description} |"
            found = True
            break

    if not found:
        raise HTTPException(status_code=404, detail=f"Control {control_id} not found")

    ANNEX_A_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"status": "updated", "control_id": control_id}


# ---------- Management Clauses parsing ----------

_CLAUSE_RE = re.compile(r"^## Clause (\d+):\s*(.+)$")
_SUB_CLAUSE_RE = re.compile(r"^### (\d+\.\d+)\s+(.+)$")
_SUB_SUB_RE = re.compile(r"^#### (\d+\.\d+\.\d+)\s+(.+)$")


def _parse_management_clauses(text: str) -> list[ManagementClause]:
    clauses: list[ManagementClause] = []
    current_clause: ManagementClause | None = None
    current_sub: SubClause | None = None
    content_lines: list[str] = []

    def _flush_sub():
        nonlocal current_sub, content_lines
        if current_sub is not None:
            current_sub.content = "\n".join(content_lines).strip()
            if current_clause is not None:
                current_clause.sub_clauses.append(current_sub)
            current_sub = None
            content_lines = []

    def _flush_clause():
        nonlocal current_clause
        _flush_sub()
        if current_clause is not None:
            clauses.append(current_clause)
            current_clause = None

    for line in text.splitlines():
        clause_match = _CLAUSE_RE.match(line)
        if clause_match:
            _flush_clause()
            current_clause = ManagementClause(
                clause_id=clause_match.group(1),
                title=clause_match.group(2).strip(),
                sub_clauses=[],
            )
            continue

        sub_match = _SUB_CLAUSE_RE.match(line)
        if sub_match and current_clause is not None:
            _flush_sub()
            current_sub = SubClause(
                sub_clause_id=sub_match.group(1),
                title=sub_match.group(2).strip(),
                content="",
            )
            continue

        # Sub-sub-clauses (#### 6.1.1) — fold into the parent sub-clause content
        sub_sub_match = _SUB_SUB_RE.match(line)
        if sub_sub_match and current_sub is not None:
            content_lines.append(f"**{sub_sub_match.group(1)} {sub_sub_match.group(2)}**")
            continue

        # Accumulate content for current sub-clause
        if current_sub is not None:
            content_lines.append(line)

    _flush_clause()
    return clauses


@router.get("/management-clauses", response_model=ManagementClausesResponse)
async def get_management_clauses():
    """Return all management clauses (4-10) parsed from the markdown reference file."""
    if not MGMT_CLAUSES_PATH.exists():
        raise HTTPException(status_code=404, detail="Management Clauses markdown file not found")
    text = MGMT_CLAUSES_PATH.read_text(encoding="utf-8")
    return ManagementClausesResponse(clauses=_parse_management_clauses(text))


@router.put("/management-clauses/{clause_id}")
async def update_management_clause(clause_id: str, body: UpdateClauseBody):
    """Update a sub-clause's content in the management clauses markdown file.

    clause_id should be a sub-clause identifier like '4.1', '5.2', etc.
    """
    if not MGMT_CLAUSES_PATH.exists():
        raise HTTPException(status_code=404, detail="Management Clauses markdown file not found")

    text = MGMT_CLAUSES_PATH.read_text(encoding="utf-8")
    lines = text.splitlines()

    # Find the sub-clause heading and replace content until next heading
    target_re = re.compile(rf"^### {re.escape(clause_id)}\s+(.+)$")
    found = False
    start_idx = -1
    end_idx = len(lines)

    for i, line in enumerate(lines):
        if target_re.match(line):
            start_idx = i + 1  # content starts after the heading
            found = True
            continue
        if found and (line.startswith("### ") or line.startswith("## ") or line.startswith("---")):
            end_idx = i
            break

    if not found:
        raise HTTPException(status_code=404, detail=f"Clause {clause_id} not found")

    # Replace content between heading and next section
    new_lines = lines[:start_idx] + ["", body.content, ""] + lines[end_idx:]
    MGMT_CLAUSES_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"status": "updated", "clause_id": clause_id}
