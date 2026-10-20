import { describe, expect, it } from 'vitest'
import router from '@/router'

describe('P2 product routes', () => {
  it('registers the core product and asset-detail pages', () => {
    const paths = router.getRoutes().map((route) => route.path)
    for (const path of [
      '/', '/catalog', '/search', '/datasets/:id', '/fields/:id',
      '/code-tables', '/code-tables/:no', '/standards', '/standards/:no',
      '/word-roots', '/word-roots/:root', '/metrics', '/metrics/:code',
      '/stat-systems', '/stat-systems/:code', '/relations/:id?', '/agent', '/overview', '/profile', '/login',
    ]) expect(paths).toContain(path)
  })

  it('preserves catalog filters and detail tab in deep-link URLs', () => {
    const catalog = router.resolve({
      name: 'catalog',
      query: { keyword: '贷款', catalog: 'FIN_STAT', page: '2' },
    })
    expect(catalog.path).toBe('/catalog')
    expect(catalog.query.keyword).toBe('贷款')
    expect(catalog.query.catalog).toBe('FIN_STAT')
    expect(catalog.query.page).toBe('2')

    const dataset = router.resolve({
      name: 'dataset',
      params: { id: 'DS000004' },
      query: { tab: 'columns' },
    })
    expect(dataset.path).toBe('/datasets/DS000004')
    expect(dataset.query.tab).toBe('columns')

    const field = router.resolve({ name: 'field', params: { id: 'COL000001' } })
    expect(field.path).toBe('/fields/COL000001')
  })
})
