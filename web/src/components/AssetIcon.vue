<template>
  <span class="asset-icon" :class="[`tone-${tone}`, { 'is-badge': mode === 'badge' }]" aria-hidden="true">
    <component :is="icon" :size="size" :stroke-width="1.9" />
  </span>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { BookOpen, Boxes, ChartNoAxesCombined, Columns3, Database, FileCheck2, Hash, LibraryBig, ShieldCheck } from 'lucide-vue-next'
const props = withDefaults(defineProps<{type:string;size?:number;mode?:'inline'|'badge'}>(),{size:22,mode:'badge'})
const map = {
  TABLE: {icon:Database,tone:'dataset'}, DATASET:{icon:Database,tone:'dataset'},
  COLUMN:{icon:Columns3,tone:'field'}, FIELD:{icon:Columns3,tone:'field'},
  STANDARD:{icon:ShieldCheck,tone:'standard'}, DATA_STANDARD:{icon:ShieldCheck,tone:'standard'},
  CODE_TABLE:{icon:Hash,tone:'code'}, REFERENCE:{icon:BookOpen,tone:'reference'},
  WORD_ROOT:{icon:LibraryBig,tone:'reference'}, METRIC:{icon:ChartNoAxesCombined,tone:'metric'},
  STAT_SYSTEM:{icon:FileCheck2,tone:'standard'}, CATALOG:{icon:Boxes,tone:'dataset'},
}
const current=computed(()=>map[props.type.toUpperCase() as keyof typeof map]||{icon:BookOpen,tone:'reference'})
const icon=computed(()=>current.value.icon)
const tone=computed(()=>current.value.tone)
</script>
<style scoped>
.asset-icon{display:inline-flex;align-items:center;justify-content:center;flex:none;vertical-align:middle;color:var(--asset-color)}
.asset-icon.is-badge{width:36px;height:36px;border-radius:10px;background:var(--asset-bg);border:1px solid var(--asset-border)}
.tone-dataset{--asset-color:#4f46e5;--asset-bg:#eef2ff;--asset-border:#dfe2ff}
.tone-field{--asset-color:#2563eb;--asset-bg:#eff6ff;--asset-border:#dbeafe}
.tone-standard{--asset-color:#059669;--asset-bg:#ecfdf5;--asset-border:#d1fae5}
.tone-code{--asset-color:#d97706;--asset-bg:#fffbeb;--asset-border:#fef3c7}
.tone-reference{--asset-color:#6d5baf;--asset-bg:#f5f3ff;--asset-border:#e9e5ff}
.tone-metric{--asset-color:#0284c7;--asset-bg:#f0f9ff;--asset-border:#dbeafe}

.asset-icon.is-badge{width:46px;height:46px;min-width:46px;border-radius:13px;box-shadow:inset 0 1px rgba(255,255,255,.95),0 5px 13px rgba(39,93,168,.09);border:1px solid rgba(67,119,205,.13)}
.asset-icon:not(.is-badge){display:inline-flex;align-items:center;justify-content:center;min-width:20px}

</style>
