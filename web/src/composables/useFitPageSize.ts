import { onBeforeUnmount, onMounted, ref, watch, type Ref } from 'vue'

/**
 * Calculate a list page size from the visible list container.
 * The list remains readable at small viewport heights and falls back to
 * natural scrolling on narrow screens.
 */
export function useFitPageSize(
  element: Ref<HTMLElement | null>,
  rowHeight: number,
  min = 5,
) {
  const pageSize = ref(min)
  let observer: ResizeObserver | undefined

  function measure() {
    const height = element.value?.clientHeight || 0
    if (height > 0) pageSize.value = Math.max(min, Math.floor(height / rowHeight))
  }

  onMounted(() => {
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(measure)
      if (element.value) observer.observe(element.value)
    }
    measure()
  })

  watch(element, (next, previous) => {
    if (previous) observer?.unobserve(previous)
    if (next) observer?.observe(next)
    measure()
  })

  onBeforeUnmount(() => observer?.disconnect())

  return pageSize
}
