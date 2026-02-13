/**
 * Assessment response types matching the backend AssessmentResponse model.
 * These types correspond to the response from POST /assessment/submit
 */

/**
 * Status of a single document in the assessment
 */
export interface DocumentResult {
  document_id: string;
  filename: string;
  status: "pending" | "processing" | "processed" | "failed";
  extracted_text_length: number;
  findings_count: number;
}

/**
 * Summary of web crawl results in assessment response
 */
export interface WebCrawlSummary {
  success: boolean;
  pages_crawled: number;
  digital_assets_found: number;
  business_context_extracted: boolean;
  organization_info_extracted: boolean;
  confidence_score: number;
  errors: string[];
  from_cache: boolean;
  business_context: Record<string, unknown> | null;
  digital_assets: Record<string, unknown>[];
  organization_info: Record<string, unknown> | null;
}

/**
 * Context node information from Neo4j
 */
export interface ContextNode {
  node_id: string;
  node_type: string;
  name: string | null;
}

/**
 * Summary of organization context stored in Neo4j
 */
export interface OrganizationContextSummary {
  created: boolean;
  organization_id: string | null;
  organization_name: string;
  industry_type: string;
  industry_sector: string | null;
  department: string;
  scope_statement_preview: string;
  web_domain: string | null;
  context_nodes: ContextNode[];
  context_nodes_created: string[];
}

/**
 * Position for React Flow node
 */
export interface GraphNodePosition {
  x: number;
  y: number;
}

/**
 * Data payload for React Flow node
 */
export interface GraphNodeData {
  label: string;
  node_type: string;
  neo4j_id: string | null;
  properties: Record<string, any>;
  [key: string]: unknown;
}

/**
 * React Flow compatible node (NEO4J_SCHEMA node types)
 */
export interface GraphNode {
  id: string;
  type:
    | "organization"
    | "industry"
    | "department"
    | "scope"
    | "context"
    | "asset"
    | "policy"
    | "document"
    | "control"
    | "default";
  position: GraphNodePosition;
  data: GraphNodeData;
}

/**
 * React Flow compatible edge
 */
export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  label: string | null;
  animated: boolean;
}

/**
 * Knowledge graph structure
 */
export interface KnowledgeGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

/**
 * Human-readable summary for frontend display
 */
export interface AssessmentSummary {
  headline: string;
  processing_time_ms: number;
  highlights: string[];
  next_step: "review_findings" | "upload_more_docs";
  next_step_url: string | null;
}

/**
 * Response acknowledging assessment submission
 * This is the main response type from POST /assessment/submit
 */
export interface AssessmentResponse {
  assessment_id: string;
  project_id: string;
  documents_received: number;
  status: "received" | "processing" | "completed" | "failed" | "partial";
  documents: DocumentResult[];
  web_crawl: WebCrawlSummary | null;
  organization_context: OrganizationContextSummary;
  knowledge_graph: KnowledgeGraph;
  summary: AssessmentSummary;
}

/**
 * Lightweight assessment record for table display
 */
export interface AssessmentRecord {
  id: string;
  version: number;
  organization_name: string;
  industry_type: string;
  department: string;
  status: "received" | "processing" | "completed" | "failed" | "partial";
  documents_count: number;
  created_at: string;
}

/**
 * Full assessment detail from GET /assessment/detail/{id}
 */
export interface AssessmentDetail {
  id: string;
  version: number;
  organization_name: string;
  nature_of_business: string;
  industry_type: string;
  department: string;
  scope_statement_isms: string;
  web_domain: string | null;
  status: string;
  documents_count: number;
  response_snapshot: Record<string, unknown> | null;
  created_at: string;
}
