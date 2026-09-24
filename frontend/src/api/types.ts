// Mirrors the backend's Pydantic response schemas (see
// backend/app/modules/*/schemas.py). Kept as plain types, not
// generated -- the backend is small and stable enough right now that a
// codegen step (e.g. openapi-typescript) would be more ceremony than
// value; revisit if the two start drifting in practice.

export type UserRole = "owner" | "admin" | "agent"

export interface User {
  id: string
  tenant_id: string
  email: string
  full_name: string | null
  role: UserRole
  is_active: boolean
}

export interface Tenant {
  id: string
  name: string
  slug: string
}

export interface KnowledgeBase {
  id: string
  tenant_id: string
  name: string
  description: string | null
  created_at: string
}

export type DocumentStatus = "pending" | "processing" | "indexed" | "failed"

export interface DocumentSummary {
  id: string
  knowledge_base_id: string
  filename: string
  content_type: string
  status: DocumentStatus
  error_message: string | null
  chunk_count: number
  created_at: string
}

export type ConversationStatus = "open" | "closed"

export interface Conversation {
  id: string
  knowledge_base_id: string
  customer_identifier: string
  status: ConversationStatus
  created_at: string
}

export interface AgentMetadata {
  route?: "answered" | "handoff"
  grounded?: boolean
  confidence?: number
  needs_retrieval?: boolean
  retrieved_chunk_count?: number
  ticket_id?: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  agent_metadata: AgentMetadata | null
  created_at: string
}

export interface ConversationWithMessages extends Conversation {
  messages: Message[]
}

export type TicketPriority = "low" | "medium" | "high" | "urgent"
export type TicketStatus = "open" | "in_progress" | "resolved" | "closed"

export interface Ticket {
  id: string
  conversation_id: string
  customer_identifier: string
  title: string
  description: string
  priority: TicketPriority
  status: TicketStatus
  created_at: string
}

export interface AnalyticsSummary {
  conversation_count: number
  message_count: number
  ticket_count: number
  tickets_by_status: Record<TicketStatus, number>
  handoff_rate: number | null
  average_confidence: number | null
}
