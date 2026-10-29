import { shallowRef } from 'vue'

export interface AssetAgentContext {
  requestId: number
  assetType: string
  assetId: string
  name: string
  technicalName: string
  task: 'ask' | 'explain' | 'sql'
}
export const assetAgentRequest = shallowRef<AssetAgentContext | null>(null)
let count=0
export function openAssetAgent(request: Omit<AssetAgentContext,'requestId'>) {
  assetAgentRequest.value={...request,requestId:++count}
}
