import { describe, expect, it } from 'vitest'
import router from '@/router'

describe('P2 product routes', () => {
  it('registers the core product and asset-detail pages', () => {
    const paths = router.getRoutes().map((route) => route.path)
    for (const path of [
      '/', '/catalog', '/search', '/datasets/:id', '/fields/:id',
      '/code-tables', '/code-tables/:no', '/standards', '/standards/:no',
      '/word-roots', '/word-roots/:root', '/metrics', '/metrics/:code',
      '/stat-systems', '/stat-systems/:code', '/overview', '/profile', '/login',
    ]) expect(paths).toContain(path)
  })
})
