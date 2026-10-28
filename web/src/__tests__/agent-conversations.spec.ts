import { beforeEach, describe, expect, it } from 'vitest'
import { useAgentConversations } from '@/composables/useAgentConversations'

beforeEach(() => {
  localStorage.clear()
})

describe('useAgentConversations', () => {
  it('persists, searches and pins conversations without a server identity dependency', () => {
    const store = useAgentConversations()
    store.load()

    const first = store.create('本期贷款余额怎么统计？', null)
    store.syncActive(
      [
        { role: 'user', text: '本期贷款余额怎么统计？' },
        { role: 'assistant', text: '使用贷款余额指标。' },
      ],
      'session-1',
      null,
    )
    store.rename(first.id, '贷款余额查询')
    store.togglePin(first.id)

    expect(store.conversations.value[0].pinned).toBe(true)
    expect(store.conversationGroups.value[0].label).toBe('置顶')

    store.searchQuery.value = '贷款余额'
    expect(store.conversationGroups.value[0].items).toHaveLength(1)

    const reloaded = useAgentConversations()
    reloaded.load()
    const restored = reloaded.restoreLast()
    expect(restored?.title).toBe('贷款余额查询')
    expect(restored?.sessionId).toBe('session-1')
    expect(restored?.pinned).toBe(true)
  })

  it('remembers free-test mode per chat while keeping official chats separate', () => {
    const store = useAgentConversations()
    store.load()
    const official = store.create('正常指标查询')
    const free = store.create('模拟数据测试', null, 'free-test')
    expect(official.modelMode).toBe('deepseek')
    expect(free.modelMode).toBe('free-test')
    store.syncActive([{ role: 'user', text: '模拟数据测试' }], 'free-test:sample123', null, 'free-test')
    const reloaded = useAgentConversations()
    reloaded.load()
    expect(reloaded.activate(free.id)?.modelMode).toBe('free-test')
    expect(reloaded.activate(official.id)?.modelMode).toBe('deepseek')
  })

  it('migrates older local history that has no pinned field', () => {
    localStorage.setItem(
      'datacontrol_agent_conversations_v1',
      JSON.stringify([
        {
          id: 'legacy-1',
          title: '旧会话',
          sessionId: null,
          createdAt: 1,
          updatedAt: 1,
          messages: [],
        },
      ]),
    )
    const store = useAgentConversations()
    store.load()
    expect(store.conversations.value[0].pinned).toBe(false)
  })
})
