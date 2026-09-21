<template>
  <section v-if="visible" class="evidence-area">
    <div v-if="evidence?.period" class="evidence-row"><span>统计期间</span><b>{{ evidence.period.label }}</b></div>
    <div v-if="evidence?.metrics?.length" class="evidence-row">
      <span>使用指标</span>
      <div class="chips">
        <span v-for="(metric, index) in evidence.metrics" :key="metric.code || metric.name || `metric-${index}`" class="evidence-chip metric">
          <BarChart3 :size="14" />{{ metric.name || metric.code }}
        </span>
      </div>
    </div>
    <div v-if="evidence?.datasets?.length" class="evidence-row">
      <span>引用资产</span>
      <div class="chips">
        <span v-for="(table, index) in evidence.datasets.slice(0, 4)" :key="table.tableName || table.name || `dataset-${index}`" class="evidence-chip">
          <Database :size="14" />{{ shortTable(table.tableName || table.name || '') }}
        </span>
      </div>
    </div>
    <div v-if="evidence?.dimensions?.length" class="evidence-row">
      <span>分析维度</span>
      <div class="chips">
        <span v-for="dimension in evidence.dimensions" :key="dimension" class="evidence-chip neutral">{{ dimensionName(dimension) }} <code>{{ dimension }}</code></span>
      </div>
    </div>
    <div v-if="evidence?.caliber" class="caliber"><span>统计口径</span><p>{{ evidence.caliber }}</p></div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { BarChart3, Database } from 'lucide-vue-next'
import type { AgentEvidence } from '@/api/client'

const props = defineProps<{ evidence?: AgentEvidence }>()

const visible = computed(() => !!(
  props.evidence?.metrics?.length ||
  props.evidence?.datasets?.length ||
  props.evidence?.dimensions?.length ||
  props.evidence?.period ||
  props.evidence?.caliber
))

function shortTable(value: string) {
  return value.includes('.') ? value.split('.').pop() || value : value
}

function dimensionName(value: string) {
  return ({
    region_code: '地区',
    org_code: '机构',
    customer_type: '客户类型',
    loan_type: '贷款类型',
    currency_cd: '币种',
    product_code: '产品',
  } as Record<string, string>)[value] || '维度'
}
</script>

<style scoped>
.evidence-area { margin-top: 15px; padding: 14px 16px; background: #e7f2f8; border: 1px solid #aacbd9; border-left: 4px solid #237fa7; border-radius: 12px; display: grid; gap: 11px; }
.evidence-row { display: grid; grid-template-columns: 82px minmax(0,1fr); gap: 10px; align-items: flex-start; }
.evidence-row > span,.caliber > span { font-size: 13px; font-weight: 800; color: #57798b; padding-top: 4px; }
.evidence-row > b { font-size: 14px; color: #204d63; padding-top: 3px; }
.chips { display: flex; flex-wrap: wrap; gap: 7px; }
.evidence-chip { display: inline-flex; align-items: center; gap: 5px; border-radius: 8px; padding: 7px 9px; background: #cee6f1; color: #155f7e; font-size: 13px; font-weight: 700; }
.evidence-chip.metric { background: #d9efe5; color: #1c6b4d; }
.evidence-chip.neutral { background: #fff; border: 1px solid #bed4df; color: #3f6679; font-weight: 650; }
.evidence-chip code { font-size: 11px; color: #5f8293; }
.caliber { display: grid; grid-template-columns: 82px minmax(0,1fr); gap: 10px; border-top: 1px solid #bfd7e2; padding-top: 10px; }
.caliber p { margin: 0; font-size: 14px; line-height: 1.7; color: #365f72; }
@media(max-width:760px){.evidence-row,.caliber{grid-template-columns:1fr;gap:4px}}
</style>
