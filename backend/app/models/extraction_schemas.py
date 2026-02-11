"""Extraction schemas for LlamaExtract document processing."""

from typing import List, Optional

from pydantic import BaseModel, Field


class PolicySection(BaseModel):
    """Extracted policy section."""

    title: str = Field(description="Section title")
    content: str = Field(description="Section content")
    controls_referenced: List[str] = Field(
        default_factory=list, description="Control IDs referenced (e.g., A.5.1, 8.1)"
    )


class ExtractedPolicy(BaseModel):
    """Schema for policy document extraction."""

    document_title: str = Field(description="Policy document title")
    version: Optional[str] = Field(None, description="Document version")
    effective_date: Optional[str] = Field(None, description="Effective date")
    owner: Optional[str] = Field(None, description="Policy owner/department")
    scope: Optional[str] = Field(None, description="Policy scope statement")
    sections: List[PolicySection] = Field(
        default_factory=list, description="Policy sections"
    )
    frameworks_mentioned: List[str] = Field(
        default_factory=list, description="Compliance frameworks mentioned"
    )


class ExtractedInvoice(BaseModel):
    """Schema for invoice extraction."""

    invoice_number: str = Field(description="Invoice number")
    invoice_date: str = Field(description="Invoice date")
    vendor_name: str = Field(description="Vendor name")
    total_amount: float = Field(description="Total amount")
    line_items: List[dict] = Field(default_factory=list, description="Line items")


class GenericDocumentExtraction(BaseModel):
    """Generic extraction schema for any document type (fallback)."""

    title: Optional[str] = Field(None, description="Document title")
    summary: Optional[str] = Field(None, description="Brief summary of content")
    key_topics: List[str] = Field(
        default_factory=list, description="Main topics covered"
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Named entities (organizations, people, systems)",
    )
    dates: List[str] = Field(
        default_factory=list, description="Important dates mentioned"
    )
    sections: List[dict] = Field(
        default_factory=list, description="Document sections with title and content"
    )
