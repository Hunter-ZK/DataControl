import { computed, ref } from 'vue'
import type { AgentConversation, AgentMessage, ContextAsset, ConversationGroup } from '@/components/agent/types'
import type { AgentModelMode } from '@/api/client'

const STORAGE_KEY = 'datacontrol_agent_conversations_v1'
const ACTIVE_KEY = 'datacontrol_agent_active_conversation_v1'
const LEGACY_REVIEW_KEY = 'datacontrol_agent_legacy_review_v1'
const MAX_CONVERSATIONS = 40
const MAX_MESSAGES_PER_CONVERSATION = 80

// Local browser history is an optional cache; the server remains the source of
// truth. Never show one account's cached conversations under another login.
function accountId(): string | null {
  try {
    const account = JSON.parse(localStorage.getItem('datacontrol_user') || '{}') as { id?: unknown }
    const id = account.id
    if (typeof id === 'number' && Number.isSafeInteger(id) && id > 0) return String(id)
    if (typeof id === 'string' && /^[1-9][0-9]{0,15}$/.test(id)) return id
  } catch { /* missing or invalid login cache */ }
  return null
}

function scopedKey(base: string): string | null {
  const id = accountId()
  return id ? `${base}_user_${id}` : null
}

function legacyUnscoped(): AgentConversation[] {
  try {
    const rows: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
    return Array.isArray(rows)
      ? rows.map(normalizeConversation).filter((item): item is AgentConversation => item !== null)
      : []
  } catch { return [] }
}

function newConversationId() {
  return `chat-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
}

function defaultTitle(value: string) {
  const normalized = value.replace(/\s+/g, ' ').trim()
  return normalized.length > 28 ? `${normalized.slice(0, 28)}…` : normalized || '新会话'
}

function normalizeConversation(value: unknown): AgentConversation | null {
  if (!value || typeof value !== 'object') return null
  const row = value as Partial<AgentConversation>
  if (typeof row.id !== 'string' || !Array.isArray(row.messages)) return null
  const now = Date.now()
  return {
    id: row.id,
    serverId: typeof row.serverId === 'string' ? row.serverId : null,
    title: typeof row.title === 'string' && row.title.trim() ? row.title.trim() : '历史会话',
    // Provider session tokens belong to the Portal, not the browser.
    sessionId: null,
    modelMode: row.modelMode === 'free-test' || (
      row.modelMode !== 'deepseek' && typeof row.sessionId === 'string'
      && row.sessionId.startsWith('free-test:')
    ) ? 'free-test' : 'deepseek',
    taskTier: row.taskTier === 'multi' ? 'multi' : 'standard',
    createdAt: typeof row.createdAt === 'number' ? row.createdAt : now,
    updatedAt: typeof row.updatedAt === 'number' ? row.updatedAt : now,
    pinned: row.pinned === true,
    messages: row.messages as AgentMessage[],
    contextAsset: row.contextAsset || null,
  }
}

export function useAgentConversations() {
  const conversations = ref<AgentConversation[]>([])
  const activeConversationId = ref<string | null>(null)
  const searchQuery = ref('')

  const activeConversation = computed(() =>
    conversations.value.find((item) => item.id === activeConversationId.value) || null,
  )

  const conversationGroups = computed<ConversationGroup[]>(() => {
    const normalizedSearch = searchQuery.value.trim().toLocaleLowerCase()
    const filtered = conversations.value.filter((conversation) => {
      if (!normalizedSearch) return true
      if (conversation.title.toLocaleLowerCase().includes(normalizedSearch)) return true
      return conversation.messages.some((message) =>
        message.text.toLocaleLowerCase().includes(normalizedSearch),
      )
    })

    const ordered = [...filtered].sort((a, b) => b.updatedAt - a.updatedAt)
    const pinned = ordered.filter((item) => item.pinned)
    const regular = ordered.filter((item) => !item.pinned)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
    const weekAgo = today - 6 * 24 * 60 * 60 * 1000
    const groups: ConversationGroup[] = []

    if (pinned.length) groups.push({ label: '置顶', items: pinned })

    const todayItems = regular.filter((item) => item.updatedAt >= today)
    const weekItems = regular.filter((item) => item.updatedAt < today && item.updatedAt >= weekAgo)
    const olderItems = regular.filter((item) => item.updatedAt < weekAgo)
    if (todayItems.length) groups.push({ label: '今天', items: todayItems })
    if (weekItems.length) groups.push({ label: '近 7 天', items: weekItems })
    if (olderItems.length) groups.push({ label: '更早', items: olderItems })
    return groups
  })

  function persist() {
    const snapshot = [...conversations.value]
      .sort((a, b) => Number(b.pinned) - Number(a.pinned) || b.updatedAt - a.updatedAt)
      .slice(0, MAX_CONVERSATIONS)
      .map((conversation) => ({
        ...conversation,
        messages: conversation.messages.slice(-MAX_MESSAGES_PER_CONVERSATION),
      }))
    conversations.value = snapshot
    const historyKey = scopedKey(STORAGE_KEY)
    const activeKey = scopedKey(ACTIVE_KEY)
    if (!historyKey || !activeKey) return
    localStorage.setItem(historyKey, JSON.stringify(snapshot))
    if (activeConversationId.value) localStorage.setItem(activeKey, activeConversationId.value)
    else localStorage.removeItem(activeKey)
  }

  function load() {
    conversations.value = []
    activeConversationId.value = null
    const historyKey = scopedKey(STORAGE_KEY)
    if (!historyKey) return
    try {
      const raw = localStorage.getItem(historyKey)
      const parsed: unknown = raw ? JSON.parse(raw) : []
      conversations.value = Array.isArray(parsed)
        ? parsed.map(normalizeConversation).filter((item): item is AgentConversation => item !== null).slice(0, MAX_CONVERSATIONS)
        : []
    } catch {
      conversations.value = []
    }
  }

  function restoreLast(): AgentConversation | null {
    const activeKey = scopedKey(ACTIVE_KEY)
    const activeId = activeKey ? localStorage.getItem(activeKey) : null
    const conversation = conversations.value.find((item) => item.id === activeId) || null
    activeConversationId.value = conversation?.id || null
    return conversation
  }

  function hasUnscopedLegacy(): boolean {
    const reviewKey = scopedKey(LEGACY_REVIEW_KEY)
    return Boolean(reviewKey && !localStorage.getItem(reviewKey) && legacyUnscoped().length)
  }

  function declineUnscopedLegacy() {
    const reviewKey = scopedKey(LEGACY_REVIEW_KEY)
    if (reviewKey) localStorage.setItem(reviewKey, 'declined')
  }

  function adoptUnscopedLegacy(): number {
    const reviewKey = scopedKey(LEGACY_REVIEW_KEY)
    if (!reviewKey) return 0
    const legacy = legacyUnscoped()
    const existingIds = new Set(conversations.value.map(c => c.id))
    let adopted = 0
    for (const row of legacy) {
      if (existingIds.has(row.id)) continue
      // The old cache did not identify its owner. Explicit import creates a
      // local draft only; never reuse an old user's serverId or dsh session.
      conversations.value.push({ ...row, serverId: null, sessionId: null })
      existingIds.add(row.id)
      adopted++
    }
    persist()
    localStorage.setItem(reviewKey, 'adopted')
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(ACTIVE_KEY)
    return adopted
  }

  function create(
    firstQuestion: string, contextAsset?: ContextAsset | null,
    modelMode: AgentModelMode = 'deepseek',
    taskTier: 'standard' | 'multi' = 'standard',
  ): AgentConversation {
    const now = Date.now()
    const conversation: AgentConversation = {
      id: newConversationId(),
      serverId: null,
      title: defaultTitle(firstQuestion),
      sessionId: null,
      modelMode,
      taskTier,
      createdAt: now,
      updatedAt: now,
      pinned: false,
      messages: [],
      contextAsset: contextAsset ? { ...contextAsset } : null,
    }
    conversations.value.unshift(conversation)
    activeConversationId.value = conversation.id
    persist()
    return conversation
  }

  function activate(id: string): AgentConversation | null {
    const conversation = conversations.value.find((item) => item.id === id) || null
    activeConversationId.value = conversation?.id || null
    persist()
    return conversation
  }

  function clearActive() {
    activeConversationId.value = null
    persist()
  }

  function syncActive(
    messages: AgentMessage[],
    sessionId: string | null,
    contextAsset?: ContextAsset | null,
    modelMode?: AgentModelMode,
  ) {
    const conversation = activeConversation.value
    if (!conversation) return
    conversation.sessionId = sessionId
    if (modelMode) conversation.modelMode = modelMode
    conversation.updatedAt = Date.now()
    conversation.messages = [...messages]
    conversation.contextAsset = contextAsset ? { ...contextAsset } : null
    persist()
  }

  function rename(id: string, title: string) {
    const conversation = conversations.value.find((item) => item.id === id)
    const normalized = title.replace(/\s+/g, ' ').trim()
    if (!conversation || !normalized) return
    conversation.title = normalized
    conversation.updatedAt = Date.now()
    persist()
  }

  function remove(id: string) {
    conversations.value = conversations.value.filter((item) => item.id !== id)
    const removedActive = activeConversationId.value === id
    if (removedActive) activeConversationId.value = null
    persist()
    return removedActive
  }

  function togglePin(id: string) {
    const conversation = conversations.value.find((item) => item.id === id)
    if (!conversation) return
    conversation.pinned = !conversation.pinned
    conversation.updatedAt = Date.now()
    persist()
  }

  function attachServerId(id: string, serverId: string) {
    const conversation = conversations.value.find((item) => item.id === id)
    if (!conversation) return
    conversation.serverId = serverId
    persist()
  }

  function mergeServer(remote: AgentConversation[]) {
    // Keep existing local IDs for active view state; server owns published turns.
    for (const incoming of remote) {
      const existing = conversations.value.find((item) => item.serverId === incoming.id || item.id === incoming.id)
      if (existing) Object.assign(existing, incoming, { id: existing.id, serverId: incoming.id })
      else conversations.value.push({ ...incoming, serverId: incoming.id })
    }
    persist()
  }

  return {
    conversations,
    activeConversationId,
    activeConversation,
    searchQuery,
    conversationGroups,
    load,
    restoreLast,
    create,
    activate,
    clearActive,
    syncActive,
    rename,
    remove,
    togglePin,
    attachServerId,
    mergeServer,
    hasUnscopedLegacy,
    adoptUnscopedLegacy,
    declineUnscopedLegacy,
  }
}
