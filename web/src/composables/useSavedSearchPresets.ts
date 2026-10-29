import { ref } from 'vue'

export type SearchPresetValues = {
  q: string
  type: string
  layer: string
  catalog: string
  status: string
}
export type SearchPreset = SearchPresetValues & {
  id: string
  name: string
  savedAt: string
}
const LIMIT = 12

function storageKey() {
  try {
    const user = JSON.parse(localStorage.getItem('datacontrol_user') || '{}') as {id?:string|number}
    return 'datacontrol_search_presets_v1_' + (user.id ? String(user.id) : 'guest')
  } catch { return 'datacontrol_search_presets_v1_guest' }
}
function normalize(x: unknown): SearchPreset | null {
  if (!x || typeof x !== 'object') return null
  const v = x as Record<string,unknown>
  if (typeof v.id !== 'string' || typeof v.name !== 'string' || !v.name.trim()) return null
  if (['q','type','layer','catalog','status'].some(key=>typeof v[key] !== 'string')) return null
  return {
    id:v.id.slice(0,100),name:v.name.trim().slice(0,36),
    q:(v.q as string).slice(0,180),type:(v.type as string).slice(0,60),
    layer:(v.layer as string).slice(0,60),catalog:(v.catalog as string).slice(0,80),
    status:(v.status as string).slice(0,60),
    savedAt:typeof v.savedAt === 'string' ? v.savedAt : '',
  }
}
function read(): SearchPreset[] {
  try{
    const raw=JSON.parse(localStorage.getItem(storageKey())||'[]') as unknown
    return Array.isArray(raw) ? raw.map(normalize).filter((x): x is SearchPreset=>!!x).slice(0,LIMIT):[]
  }catch{return []}
}
export function useSavedSearchPresets(){
  const presets=ref<SearchPreset[]>(read())
  function persist(items: SearchPreset[]) {
    const value=items.slice(0,LIMIT)
    localStorage.setItem(storageKey(),JSON.stringify(value))
    presets.value=value
  }
  function save(name:string,filters:SearchPresetValues) {
    const clean=name.trim().slice(0,36)
    if(!clean)throw new Error('请输入筛选方案名称')
    const same=presets.value.find(x=>x.name===clean)
    if(!same && presets.value.length>=LIMIT)throw new Error('最多保存 12 套筛选方案，请先删除不需要的方案')
    const item:SearchPreset={
      id:same?.id || crypto.randomUUID(),name:clean,
      q:filters.q.trim(),type:filters.type,layer:filters.layer,
      catalog:filters.catalog,status:filters.status,savedAt:new Date().toISOString(),
    }
    persist([item,...presets.value.filter(x=>x.id!==item.id)])
  }
  function remove(id:string){persist(presets.value.filter(x=>x.id!==id))}
  function refresh(){presets.value=read()}
  return {presets,save,remove,refresh}
}
