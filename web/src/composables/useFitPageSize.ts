import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'

interface FitPageOptions {
  rowHeight: number
  reserved?: number
  min?: number
  max?: number
}

/** Compute a page size from an actual, bounded work area, rather than screen heuristics. */
export function useFitPageSize(target: Ref<HTMLElement|null>, options: FitPageOptions): Ref<number> {
  const minimum=options.min??5
  const maximum=Math.max(minimum,options.max??20)
  const pageSize=ref(minimum)
  let observer: ResizeObserver|null=null
  const measure=(height:number)=>{
    if(!Number.isFinite(height)||height<=0)return
    const available=Math.max(0,height-(options.reserved??0))
    pageSize.value=Math.min(maximum,Math.max(minimum,Math.floor(available/options.rowHeight)))
  }
  const connect=(element:HTMLElement|null)=>{
    observer?.disconnect();observer=null
    if(!element)return
    measure(element.getBoundingClientRect().height)
    if(typeof ResizeObserver!=='undefined'){
      observer=new ResizeObserver(entries=>{const entry=entries[0];if(entry)measure(entry.contentRect.height)})
      observer.observe(element)
    }
  }
  onMounted(()=>connect(target.value))
  watch(target,element=>connect(element))
  onBeforeUnmount(()=>observer?.disconnect())
  return pageSize
}
