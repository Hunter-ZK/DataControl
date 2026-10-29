import {describe,it,expect} from 'vitest'
import {validateNamingRows,missingRoots,type NamingRow} from '@/utils/namingReview'
const row=(name:string,finalName:string,key:number):NamingRow=>({
  key,cnName:name,finalName,suggestedName:'',segments:[],source:'人工待补充',
  issues:[],status:'待确认',existingCandidates:[],original:{},confirmed:false,note:'',
})
describe('naming review safeguards',()=>{
  it('flags duplicates, invalid identifiers and reserved words',()=>{
    const errors=validateNamingRows([row('A','loan_bal',0),row('B','LOAN_BAL',1),row('C','select',2)],64)
    expect(errors.get(0)).toContain('本批次重名')
    expect(errors.get(1)?.length).toBeGreaterThan(0)
    expect(errors.get(2)).toContain('英文名不符合规范或使用了保留字')
  })
  it('aggregates unknown terms without proposing fake abbreviations',()=>{
    const a=row('客户放款','',0);a.segments=[{cn:'放款',root:'',source:'missing'}]
    const b=row('放款余额','',1);b.segments=[{cn:'放款',root:'',source:'missing'}]
    expect(missingRoots([a,b])).toEqual([{cn:'放款',abbr:'',full:'',count:2,examples:'客户放款、放款余额'}])
  })
})
