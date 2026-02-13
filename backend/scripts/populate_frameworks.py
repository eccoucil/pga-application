import asyncio
import json
import re
from pathlib import Path
from typing import List, Dict, Any

from supabase import create_client
import sys
import os

# Add the backend directory to sys.path to import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.config import get_settings

def parse_iso_annex_a(file_path: Path) -> List[Dict[str, Any]]:
    text = file_path.read_text(encoding="utf-8")
    requirements = []
    
    section_re = re.compile(r"^## (\d+)\.\s+(.+?)(?:\s*\(\d+ controls?\))?\s*$")
    row_re = re.compile(r"^\|\s*(\d+\.\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$")
    
    current_category_code = ""
    current_category_name = ""
    
    for line in text.splitlines():
        sec_match = section_re.match(line)
        if sec_match:
            current_category_code = f"A.{sec_match.group(1)}"
            current_category_name = sec_match.group(2).strip()
            continue
            
        row_match = row_re.match(line)
        if row_match:
            identifier, title, description = row_match.groups()
            if identifier.replace("-", "").strip() == "":
                continue
                
            requirements.append({
                "identifier": f"A.{identifier.strip()}",
                "title": title.strip(),
                "description": description.strip(),
                "clause_type": "domain",
                "category_code": current_category_code,
                "category": current_category_name,
                "is_mandatory_doc": False
            })
            
    return requirements

def parse_iso_management(file_path: Path) -> List[Dict[str, Any]]:
    text = file_path.read_text(encoding="utf-8")
    requirements = []
    
    clause_re = re.compile(r"^## Clause (\d+):\s*(.+)$")
    sub_re = re.compile(r"^### (\d+\.\d+)\s+(.+)$")
    
    current_clause_id = ""
    current_clause_title = ""
    
    lines = text.splitlines()
    for i, line in enumerate(lines):
        clause_match = clause_re.match(line)
        if clause_match:
            current_clause_id = clause_match.group(1)
            current_clause_title = clause_match.group(2).strip()
            continue
            
        sub_match = sub_re.match(line)
        if sub_match:
            sub_id, sub_title = sub_match.groups()
            
            content_lines = []
            for j in range(i + 1, len(lines)):
                next_line = lines[j]
                if next_line.startswith("##") or next_line.startswith("---") or next_line.startswith("### "):
                    break
                content_lines.append(next_line)
            
            requirements.append({
                "identifier": sub_id.strip(),
                "title": sub_title.strip(),
                "description": "\n".join(content_lines).strip(),
                "clause_type": "management",
                "category_code": current_clause_id,
                "category": current_clause_title,
                "is_mandatory_doc": False
            })
            
    return requirements

def parse_bnm_rmit(file_path: Path) -> List[Dict[str, Any]]:
    text = file_path.read_text(encoding="utf-8")
    requirements = []
    
    section_re = re.compile(r"^## (\d+)\.\s+(.+)$")
    sub_re = re.compile(r"^###\s+(.+)$")
    req_re = re.compile(r"^\*\*(S|G)\s+(\d+\.\d+)\*\*\s+(.+)$")
    
    current_sec_num = 0
    current_sec_title = ""
    current_sub_title = ""
    
    lines = text.splitlines()
    for i, line in enumerate(lines):
        sec_match = section_re.match(line)
        if sec_match:
            current_sec_num = int(sec_match.group(1))
            current_sec_title = sec_match.group(2).strip()
            current_sub_title = ""
            continue
            
        sub_match = sub_re.match(line)
        if sub_match:
            current_sub_title = sub_match.group(1).strip()
            continue
            
        req_match = req_re.match(line)
        if req_match:
            rtype_char, ref_id, first_line = req_match.groups()
            rtype = "standard" if rtype_char == "S" else "guidance"
            
            content_lines = [first_line]
            sub_reqs = []
            
            # Sub-requirement pattern: (a) Text...
            sub_item_re = re.compile(r"^\(([a-z])\)\s+(.+)$")
            
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if next_line.startswith("**S") or next_line.startswith("**G") or next_line.startswith("##"):
                    break
                
                sub_item_match = sub_item_re.match(next_line)
                if sub_item_match:
                    sub_reqs.append({
                        "key": sub_item_match.group(1),
                        "text": sub_item_match.group(2).strip()
                    })
                elif not sub_reqs: # Only add to main text if we haven't started sub-reqs
                    content_lines.append(lines[j])
                
            requirements.append({
                "reference_id": f"{rtype_char} {ref_id}",
                "section_number": current_sec_num,
                "section_title": current_sec_title,
                "subsection_title": current_sub_title,
                "requirement_text": "\n".join(content_lines).strip(),
                "requirement_type": rtype,
                "sub_requirements": sub_reqs,
                "part": "B"
            })
            
    return requirements

async def main():
    settings = get_settings()
    supabase = create_client(settings.supabase_url, settings.supabase_service_key)
    
    base_dir = Path(__file__).resolve().parents[2]
    docs_dir = base_dir / "docs" / "framework"
    
    print("Parsing ISO Annex A...")
    iso_annex_a = parse_iso_annex_a(docs_dir / "iso27001-2022-annex-a-controls.md")
    
    print("Parsing ISO Management Clauses...")
    iso_mgmt = parse_iso_management(docs_dir / "iso27001-2022-management-clauses.md")
    
    print("Parsing BNM RMIT...")
    bnm_rmit = parse_bnm_rmit(base_dir / "BNM_RMIT_Policy_Requirements.md")
    
    # Insert ISO
    all_iso = iso_annex_a + iso_mgmt
    print(f"Inserting {len(all_iso)} ISO requirements...")
    for i in range(0, len(all_iso), 50):
        batch = all_iso[i:i+50]
        supabase.table("iso_requirements").upsert(batch, on_conflict="identifier").execute()
        
    # Insert BNM
    print(f"Inserting {len(bnm_rmit)} BNM RMIT requirements...")
    for i in range(0, len(bnm_rmit), 50):
        batch = bnm_rmit[i:i+50]
        supabase.table("bnm_rmit_requirements").upsert(batch, on_conflict="reference_id").execute()
        
    print("Done!")

if __name__ == "__main__":
    asyncio.run(main())