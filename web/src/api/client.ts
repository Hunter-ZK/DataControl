import axios, { type AxiosRequestConfig } from 'axios'

const http = axios.create({ baseURL: '/api/v1', timeout: 120000 })
http.interceptors.request.use((config) => { const token=localStorage.getItem('datacontrol_token'); if(token) config.headers.Authorization=`Bearer ${token}`; return config })
async function get<T>(url:string,config?:AxiosRequestConfig):Promise<T>{const r=await http.get<{code:string;data:T}>(url,config);return r.data.data}
async function post<T>(url:string,body?:unknown):Promise<T>{const r=await http.post<{code:string;data:T}>(url,body);return r.data.data}
async function remove<T>(url:string):Promise<T>{const r=await http.delete<{code:string;data:T}>(url);return r.data.data}

export interface SearchItem{assetId:string;assetType:string;title:string;technicalName:string;titleHighlight:string;technicalNameHighlight:string;snippet:string;score:number;catalogCode?:string|null;layerCode?:string|null;status?:string|null;parentAssetId?:string|null}
export interface SearchResponse{query:string;total:number;offset:number;limit:number;items:SearchItem[];facets:{assetTypes:Record<string,number>;layers:Record<string,number>;catalogs:Record<string,number>;statuses:Record<string,number>}}
export interface SearchSuggestion{assetId:string;assetType:string;title:string;technicalName:string}
export interface RelationNode{assetId:string;name:string;tableName?:string|null;layerCode?:string|null;catalogCode?:string|null;status?:string|null;isCenter?:boolean}
export interface RelationEdge{id:number;source:string;target:string;taskName?:string|null;evidence:string}
export interface RelationGraph{centerAssetId:string;depth:number;direction:string;truncated:boolean;nodes:RelationNode[];edges:RelationEdge[];impactCount?:number;impactByLayer?:Record<string,number>}
export interface AgentStatus{ready:boolean;mode:string;source:string;gatewayUrl:string;provider:string;model:string;sourceMigrated:boolean;sessionBridgeImplemented:boolean;integrated:boolean;realModelAccepted:boolean;serviceReachable:boolean;nextGate?:string|null;reason?:string|null;sqlExecutionEnabled:boolean;hiddenReasoningExposed:boolean}
export interface AgentActivity{type:string;phase?:string;callId?:string;tool?:string;status?:string;input?:unknown;reason?:string}
export interface AgentMetricEvidence{code?:string|null;name?:string|null;sourceEntity?:string|null;measure?:string|null;timeField?:string|null;validDimensions?:string[]}
export interface AgentDatasetEvidence{tableName?:string|null;name?:string|null}
export interface AgentEvidence{metrics?:AgentMetricEvidence[];datasets?:AgentDatasetEvidence[];dimensions?:string[];period?:{label:string;resolved:string}|null;caliber?:string|null;warnings?:string[]}
export interface AgentResult{sessionId?:string|null;answer:string;summary?:string|null;stopReason?:string|null;events?:AgentActivity[];sql?:string|null;validation?:any;evidence?:AgentEvidence;sqlExecuted:boolean;hiddenReasoningExposed:boolean}

const api={get,post,delete:remove};export default api
export const assetApi={overview:()=>get<Record<string,any>>('/home/overview'),catalogs:()=>get<any[]>('/catalogs'),tables:(params?:Record<string,unknown>)=>get<any[]>('/tables',{params}),table:(id:string)=>get<any>(`/tables/${id}`),columns:(params?:Record<string,unknown>)=>get<any[]>('/columns',{params}),search:(q:string,params?:Record<string,unknown>)=>get<SearchResponse>('/search',{params:{q,...params}}),suggest:(q:string,limit=8)=>get<SearchSuggestion[]>('/search/suggest',{params:{q,limit}}),tags:(id:string)=>get<any[]>(`/tables/${id}/tags`),changes:(id:string)=>get<any[]>(`/tables/${id}/changes`),commonSql:(id:string)=>get<any[]>(`/tables/${id}/common-sql`),relations:(id:string)=>get<any>(`/relations/tables/${id}`),reference:(endpoint:string,keyword?:string)=>get<any[]>(endpoint,{params:keyword?{keyword}:undefined})}
export const relationApi={graph:(id:string,params?:Record<string,unknown>)=>get<RelationGraph>(`/relations/graph/${id}`,{params}),impact:(id:string,params?:Record<string,unknown>)=>get<RelationGraph>(`/relations/impact/${id}`,{params}),path:(source:string,target:string,maxDepth=8)=>get<any>('/relations/path',{params:{source,target,max_depth:maxDepth}})}
export const agentApi={status:()=>get<AgentStatus>('/agent/status'),query:(question:string,sessionId?:string|null)=>post<AgentResult>('/agent/query',{question,sessionId:sessionId||undefined})}
export const authApi={login:(username:string,password:string)=>post<any>('/auth/login',{username,password}),me:()=>get<any>('/auth/me')}
export const activityApi={favorites:()=>get<any[]>('/activity/favorites'),recent:()=>get<any[]>('/activity/recent-views'),history:()=>get<any[]>('/activity/search-history'),recordSearch:(keyword:string)=>post('/activity/search-history',{keyword}),recordView:(assetId:string)=>post('/activity/views',{assetType:'TABLE',assetId})}
