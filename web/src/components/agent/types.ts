import type {
  AgentActivity,
  AgentEvidence,
  AgentValidation,
  AgentValidationState,
} from '@/api/client'

export type AgentMessage = {
  role: 'user' | 'assistant'
  text: string
  summary?: string | null
  sql?: string | null
  validation?: AgentValidation | null
  validationState?: AgentValidationState
  events?: AgentActivity[]
  evidence?: AgentEvidence
}

export type ContextAsset = {
  assetId: string
  tableName: string
  bizName?: string | null
}

export type AgentConversation = {
  id: string
  title: string
  sessionId: string | null
  createdAt: number
  updatedAt: number
  pinned: boolean
  messages: AgentMessage[]
  contextAsset?: ContextAsset | null
}

export type ConversationGroup = {
  label: string
  items: AgentConversation[]
}

export type ProcessStep = {
  callId: string
  tool: string
  label: string
  status: 'done' | 'error' | 'running'
}
