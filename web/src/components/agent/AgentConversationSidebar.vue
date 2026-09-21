<template>
  <aside class="history-pane">
    <div class="history-head">
      <div class="history-meta">
        <span>对话记录</span>
        <b>{{ count }}</b>
      </div>
      <button class="history-new" :disabled="loading" @click="$emit('new')"><Plus :size="16" />新会话</button>
      <label class="history-search">
        <Search :size="15" />
        <input
          :value="searchQuery"
          type="search"
          placeholder="搜索对话"
          @input="$emit('update:searchQuery', ($event.target as HTMLInputElement).value)"
        />
      </label>
    </div>

    <div class="history-scroll">
      <template v-if="groups.length">
        <section v-for="group in groups" :key="group.label" class="history-group">
          <div class="history-group-title">{{ group.label }}</div>
          <div
            v-for="conversation in group.items"
            :key="conversation.id"
            class="history-item"
            :class="{ active: conversation.id === activeId }"
          >
            <button class="history-select" :disabled="loading" @click="$emit('select', conversation)">
              <Pin v-if="conversation.pinned" :size="13" class="pin-mark" />
              <MessageSquare v-else :size="15" />
              <span>{{ conversation.title }}</span>
            </button>
            <div class="history-item-actions">
              <button :title="conversation.pinned ? '取消置顶' : '置顶'" @click="$emit('togglePin', conversation)">
                <PinOff v-if="conversation.pinned" :size="13" />
                <Pin v-else :size="13" />
              </button>
              <button title="重命名" @click="$emit('rename', conversation)"><Pencil :size="13" /></button>
              <button title="删除" @click="$emit('delete', conversation)"><Trash2 :size="13" /></button>
            </div>
          </div>
        </section>
      </template>
      <div v-else class="history-empty">
        <Search v-if="searchQuery" :size="20" />
        <MessageSquare v-else :size="20" />
        <b>{{ searchQuery ? '没有匹配的对话' : '暂无历史对话' }}</b>
        <span>{{ searchQuery ? '尝试更换关键词。' : '发起第一次问数后，会自动保存在当前浏览器。' }}</span>
      </div>
    </div>

    <div class="history-foot"><ShieldCheck :size="13" />对话保存在当前浏览器</div>
  </aside>
</template>

<script setup lang="ts">
import { MessageSquare, Pencil, Pin, PinOff, Plus, Search, ShieldCheck, Trash2 } from 'lucide-vue-next'
import type { AgentConversation, ConversationGroup } from '@/components/agent/types'

defineProps<{
  groups: ConversationGroup[]
  count: number
  activeId: string | null
  loading: boolean
  searchQuery: string
}>()

defineEmits<{
  new: []
  select: [conversation: AgentConversation]
  rename: [conversation: AgentConversation]
  delete: [conversation: AgentConversation]
  togglePin: [conversation: AgentConversation]
  'update:searchQuery': [value: string]
}>()
</script>

<style scoped>
.history-pane { min-width: 0; display: flex; flex-direction: column; background: #e7f2f8; border-right: 1px solid #aacbda; }
.history-head { padding: 16px 14px 13px; border-bottom: 1px solid #bcd6e2; }
.history-meta { display: flex; align-items: center; justify-content: space-between; color: #315f76; font-size: 14px; margin-bottom: 10px; }
.history-meta b { min-width: 25px; text-align: center; padding: 2px 7px; border-radius: 999px; background: #c3e0ed; color: #155d7e; font-size: 12px; }
.history-new { width: 100%; display: flex; align-items: center; justify-content: center; gap: 7px; border: 1px solid #126f9a; background: #147ba7; color: #fff; border-radius: 10px; padding: 10px 12px; font-size: 14px; font-weight: 750; cursor: pointer; box-shadow: 0 6px 15px rgba(22,113,154,.17); }
.history-new:hover { background: #0f678e; }
.history-new:disabled { opacity: .5; cursor: not-allowed; }
.history-search { margin-top: 10px; height: 38px; display: flex; align-items: center; gap: 7px; padding: 0 10px; border: 1px solid #aecdda; border-radius: 9px; background: rgba(255,255,255,.8); color: #648597; }
.history-search:focus-within { border-color: #4c9dbc; box-shadow: 0 0 0 3px rgba(44,139,178,.1); }
.history-search input { min-width: 0; flex: 1; border: 0; outline: 0; background: transparent; color: #29576d; font-size: 13px; }
.history-search input::placeholder { color: #809aa7; }
.history-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 12px 9px; }
.history-group + .history-group { margin-top: 15px; }
.history-group-title { padding: 0 8px 6px; color: #58798b; font-size: 11px; font-weight: 800; letter-spacing: .04em; }
.history-item { position: relative; display: grid; grid-template-columns: minmax(0,1fr) auto; align-items: center; gap: 3px; border: 1px solid transparent; border-radius: 10px; margin-bottom: 3px; }
.history-item:hover { background: #d8eaf3; border-color: #b5d3e0; }
.history-item.active { background: #c6e3f0; border-color: #80b7ce; box-shadow: inset 3px 0 0 #147aa5; }
.history-select { min-width: 0; display: flex; align-items: center; gap: 8px; border: 0; background: transparent; padding: 10px 5px 10px 9px; color: #285970; cursor: pointer; text-align: left; }
.history-select:disabled { cursor: default; }
.history-select span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 650; }
.pin-mark { color: #0e719c; fill: rgba(14,113,156,.14); }
.history-item-actions { display: flex; align-items: center; gap: 2px; padding-right: 5px; opacity: 0; transition: opacity .15s ease; }
.history-item:hover .history-item-actions,.history-item.active .history-item-actions { opacity: 1; }
.history-item-actions button { width: 27px; height: 27px; display: grid; place-items: center; border: 0; border-radius: 7px; background: rgba(255,255,255,.84); color: #4f7487; cursor: pointer; }
.history-item-actions button:hover { color: #0d668f; background: #fff; }
.history-empty { margin: 30px 12px; padding: 18px 12px; display: grid; justify-items: center; gap: 7px; text-align: center; color: #6f8d9d; border: 1px dashed #adcbd8; border-radius: 12px; background: rgba(255,255,255,.46); }
.history-empty b { font-size: 13px; color: #426c80; }
.history-empty span { font-size: 12px; line-height: 1.55; }
.history-foot { flex: none; display: flex; align-items: center; justify-content: center; gap: 5px; padding: 11px 8px; border-top: 1px solid #bcd6e2; color: #628090; font-size: 11px; }
</style>
