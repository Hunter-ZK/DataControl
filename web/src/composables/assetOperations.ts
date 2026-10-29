import { shallowRef } from 'vue'

export interface AssetOperation {
  id: string
  label: string
  group: '常用' | '导出' | '生成' | '分析' | '问 Agent'
}
export interface ActiveAssetOperations {
  owner: symbol
  path: string
  label: string
  actions: AssetOperation[]
  execute: (id: string) => void
}
export const activeAssetOperations = shallowRef<ActiveAssetOperations | null>(null)
