<template>
  <section class="clarification-card" :class="{ resolved }">
    <div class="clarification-head">
      <span class="icon"><CircleHelp :size="17" /></span>
      <div>
        <b>{{ clarification.question }}</b>
        <p>仅基于 DataControl 内部可信语义，请选择本次要采用的口径。</p>
      </div>
      <span class="policy"><ShieldCheck :size="13" />内部证据</span>
    </div>

    <div v-if="clarification.options.length" class="option-list">
      <button
        v-for="option in clarification.options"
        :key="option.id"
        type="button"
        class="option-card"
        :class="{ selected: selected.includes(option.value) }"
        :disabled="resolved"
        @click="toggle(option.value)"
      >
        <span class="selector"><Check v-if="selected.includes(option.value)" :size="13" /></span>
        <div>
          <b>{{ option.label }}</b>
          <p>{{ option.description }}</p>
          <code v-if="option.metadata?.sourceEntity">{{ option.metadata.sourceEntity }}</code>
        </div>
      </button>
    </div>

    <div v-if="clarification.allow_custom_input && !resolved" class="custom-row">
      <input v-model="custom" placeholder="以上都不符合时，可补充业务口径或指标名称" @keydown.enter.prevent="confirmCustom" />
      <button type="button" :disabled="!custom.trim()" @click="confirmCustom">使用补充说明</button>
    </div>

    <div v-if="!resolved && clarification.options.length" class="clarification-actions">
      <span>{{ clarification.selection_mode === 'multiple' ? '可多选' : '单选' }} · 选择后继续原问题，无需重新描述</span>
      <button type="button" class="confirm" :disabled="selected.length === 0" @click="confirmSelection">确认并继续</button>
    </div>

    <div v-if="resolved" class="resolved-row">
      <CheckCircle2 :size="16" />
      <span>已选择：</span>
      <b>{{ selectedLabels.join('、') || '已补充业务口径' }}</b>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Check, CheckCircle2, CircleHelp, ShieldCheck } from 'lucide-vue-next'
import type { AgentClarification } from '@/api/client'

const props = defineProps<{
  clarification: AgentClarification
  resolved?: boolean
  selection?: string[]
}>()

const emit = defineEmits<{
  clarify: [payload: { values: string[]; labels: string[]; custom?: string }]
}>()

const selected = ref<string[]>([...(props.selection || [])])
const custom = ref('')

watch(
  () => props.selection,
  (value) => { selected.value = [...(value || [])] },
)

const selectedLabels = computed(() => selected.value.map((value) => {
  const option = props.clarification.options.find((item) => item.value === value)
  return option?.label || value
}))

function toggle(value: string) {
  if (props.resolved) return
  if (props.clarification.selection_mode === 'multiple') {
    selected.value = selected.value.includes(value)
      ? selected.value.filter((item) => item !== value)
      : [...selected.value, value]
    return
  }
  selected.value = [value]
}

function confirmSelection() {
  if (!selected.value.length || props.resolved) return
  emit('clarify', { values: [...selected.value], labels: selectedLabels.value })
}

function confirmCustom() {
  const value = custom.value.trim()
  if (!value || props.resolved) return
  emit('clarify', { values: [], labels: [], custom: value })
}
</script>

<style scoped>
.clarification-card{margin-top:16px;border:1.5px solid #9fc9da;border-radius:13px;background:linear-gradient(180deg,#f4fbfe,#fff);overflow:hidden;box-shadow:0 8px 24px rgba(38,104,135,.08)}.clarification-card.resolved{border-color:#bcd8cb;background:#f7fcf9}.clarification-head{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:10px;align-items:start;padding:14px 15px;border-bottom:1px solid #dcecf3}.clarification-head .icon{width:30px;height:30px;border-radius:9px;display:grid;place-items:center;background:#d9eef7;color:#176e95}.clarification-head b{display:block;font-size:14px;line-height:1.55;color:#173f53}.clarification-head p{font-size:11px;line-height:1.55;color:#668391;margin:4px 0 0}.policy{display:flex;align-items:center;gap:4px;font-size:9px;font-weight:700;color:#357663;background:#e8f5ef;border:1px solid #c7e5d7;border-radius:999px;padding:5px 7px;white-space:nowrap}.option-list{display:grid;gap:8px;padding:12px 14px}.option-card{width:100%;display:grid;grid-template-columns:22px minmax(0,1fr);gap:9px;text-align:left;padding:11px 12px;border:1px solid #d5e5ec;border-radius:10px;background:#fff;color:#294f62;cursor:pointer;transition:.15s ease}.option-card:hover:not(:disabled){border-color:#72b4cd;background:#f5fbfd}.option-card.selected{border-color:#2486ad;background:#eaf7fb;box-shadow:inset 0 0 0 1px rgba(36,134,173,.12)}.option-card:disabled{cursor:default}.selector{width:18px;height:18px;border:1.5px solid #9ab7c5;border-radius:50%;display:grid;place-items:center;color:#fff;margin-top:1px}.option-card.selected .selector{background:#2184aa;border-color:#2184aa}.option-card b{font-size:12px}.option-card p{font-size:10px;line-height:1.5;color:#687f8c;margin:4px 0}.option-card code{font-size:9px;color:#6b8795}.custom-row{display:flex;gap:7px;padding:0 14px 12px}.custom-row input{flex:1;height:36px;border:1px solid #d0e1e8;border-radius:8px;padding:0 10px;outline:none;font-size:11px}.custom-row input:focus{border-color:#66abc6}.custom-row button,.confirm{border:0;border-radius:8px;background:#1c7da5;color:#fff;padding:0 12px;font-size:10px;font-weight:700;cursor:pointer}.custom-row button:disabled,.confirm:disabled{opacity:.4;cursor:not-allowed}.clarification-actions{display:flex;justify-content:space-between;align-items:center;padding:10px 14px;border-top:1px solid #e2edf2;background:#fbfdfe}.clarification-actions>span{font-size:9px;color:#758d99}.confirm{height:32px}.resolved-row{display:flex;align-items:center;gap:6px;padding:11px 14px;color:#28745a;font-size:10px;border-top:1px solid #dcece4}.resolved-row b{font-size:11px}@media(max-width:650px){.clarification-head{grid-template-columns:auto 1fr}.policy{grid-column:2;justify-self:start}.custom-row{flex-direction:column}.custom-row button{height:34px}.clarification-actions{align-items:flex-start;gap:8px;flex-direction:column}.confirm{width:100%}}
</style>
