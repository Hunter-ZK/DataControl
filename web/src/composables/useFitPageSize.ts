import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'
export function useFitPageSize(
  el: Ref<HTMLElement | null>, rowHeight: number, minimum = 4,
) {
  const pageSize = ref(minimum)
  let observer: ResizeObserver | undefined
  onMounted(() => {
    if (typeof ResizeObserver === 'undefined') return
    observer = new ResizeObserver(([entry]) => {
      if (!entry) return
      pageSize.value = Math.max(minimum, Math.floor(entry.contentRect.height / rowHeight))
    })
    watch(el, (element, oldElement) => {
      if (oldElement) observer?.unobserve(oldElement)
      if (element) observer?.observe(element)
    }, { immediate: true })
  })
  onBeforeUnmount(() => observer?.disconnect())
  return pageSize
}
