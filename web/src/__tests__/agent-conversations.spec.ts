import { beforeEach, describe, expect, it } from 'vitest'
import { useAgentConversations } from '@/composables/useAgentConversations'

beforeEach(() => {
  localStorage.clear()
  localStorage.setItem('datacontrol_user', JSON.stringify({ id: 1, username: 'demo' }))
})

describe('useAgentConversations', () => {
  it('persists, searches and pins conversations within the signed-in account', () => {
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
    expect(restored?.sessionId).toBeNull()
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
    expect(store.conversations.value).toHaveLength(0)
    expect(store.hasUnscopedLegacy()).toBe(true)
    expect(store.adoptUnscopedLegacy()).toBe(1)
    expect(store.conversations.value[0].pinned).toBe(false)
    expect(localStorage.getItem('datacontrol_agent_conversations_v1')).toBeNull()
  })
  it('merges remote conversations without losing local-only history or changing active IDs', () => {
    const store = useAgentConversations()
    store.load()
    const local = store.create('本地草稿')
    store.syncActive([{ role: 'user', text: '本地问题' }], null)
    const remoteData = {
      id: '11111111-1111-4111-8111-111111111111',
      title: '远程记录', sessionId: 'remote-session', modelMode: 'deepseek' as const,
      createdAt: 100, updatedAt: 200, pinned: false,
      messages: [{ role: 'user' as const, text: '远程问题' }],
    }
    store.mergeServer([remoteData])
    expect(store.conversations.value).toHaveLength(2)
    expect(store.activeConversationId.value).toBe(local.id)
    expect(store.conversations.value.find(c => c.serverId === remoteData.id)?.sessionId).toBeNull()
    store.attachServerId(local.id, '22222222-2222-4222-8222-222222222222')
    store.mergeServer([{
      ...remoteData, id: '22222222-2222-4222-8222-222222222222',
      messages: [{ role: 'user', text: '服务端是最终事实' }],
    }])
    expect(store.conversations.value).toHaveLength(2)
    expect(store.activeConversationId.value).toBe(local.id)
    expect(store.activeConversation.value?.messages[0].text).toBe('服务端是最终事实')
    const loaded = useAgentConversations()
    loaded.load()
    expect(loaded.conversations.value.find(c => c.id === local.id)?.serverId)
      .toBe('22222222-2222-4222-8222-222222222222')
  })

  it('keeps user A cached history separate from user B', () => {
    const userA = useAgentConversations()
    userA.load()
    const first = userA.create('用户 A 的问题')
    userA.syncActive([{ role: 'user', text: '私有记录' }], null)

    localStorage.setItem('datacontrol_user', JSON.stringify({ id: 2, username: 'admin' }))
    const userB = useAgentConversations()
    userB.load()
    expect(userB.conversations.value).toHaveLength(0)
    userB.create('用户 B 的问题')

    localStorage.setItem('datacontrol_user', JSON.stringify({ id: 1, username: 'demo' }))
    const restored = useAgentConversations()
    restored.load()
    expect(restored.conversations.value).toHaveLength(1)
    expect(restored.conversations.value[0].id).toBe(first.id)
  })

})
