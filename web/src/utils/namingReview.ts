export interface NamingSuggestion {
  cnName: string
  suggestedName: string
  segments: Array<{ cn: string; root: string; source: string }>
  source: string
  issues: string[]
  status: string
  existingCandidates: string[]
}
export interface NamingRow extends NamingSuggestion {
  key: number
  original: Record<string, string>
  finalName: string
  confirmed: boolean
  note: string
}
const identifier = /^[a-z][a-z0-9_]*$/
const reserved = new Set(['select','from','where','group','order','table','date','user','index','by','desc'])
export function validateNamingRows(rows: NamingRow[], maxLength: number): Map<number, string[]> {
  const counts = new Map<string, number>()
  rows.forEach(row => { if (row.finalName.trim()) {
    const key = row.finalName.trim().toLowerCase(); counts.set(key,(counts.get(key)||0)+1)
  } })
  return new Map(rows.map(row=>{
    const name = row.finalName.trim()
    const messages: string[] = []
    if (!identifier.test(name) || reserved.has(name)) messages.push('英文名不符合规范或使用了保留字')
    if (name.length > maxLength) messages.push('超过长度上限 '+maxLength)
    if (name && (counts.get(name.toLowerCase())||0)>1) messages.push('本批次重名')
    return [row.key,messages]
  }))
}
export function missingRoots(rows: NamingRow[]) {
  const map = new Map<string,{cn:string;abbr:string;full:string;count:number;examples:string}>()
  for (const row of rows) for(const part of row.segments) if(!part.root){
    const existing=map.get(part.cn)
    if(existing) {existing.count++;if(!existing.examples.includes(row.cnName))existing.examples+= '、'+row.cnName}
    else map.set(part.cn,{cn:part.cn,abbr:'',full:'',count:1,examples:row.cnName})
  }
  return Array.from(map.values())
}
