export type DocumentStatus = 'uploading' | 'processing' | 'ready' | 'error'

export interface ProjectDocument {
  id: string
  client_id: string
  project_id: string
  user_id: string
  filename: string
  format: string
  character_count: number
  word_count: number
  num_chunks: number
  extraction_confidence: number | null
  processing_time_ms: number | null
  metadata: Record<string, unknown>
  intake_document_id: string | null
  status: DocumentStatus
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface CreateDocumentData {
  filename: string
  format: string
  character_count?: number
  word_count?: number
  num_chunks?: number
  extraction_confidence?: number
  processing_time_ms?: number
  metadata?: Record<string, unknown>
  intake_document_id?: string
  status?: DocumentStatus
  error_message?: string
}
