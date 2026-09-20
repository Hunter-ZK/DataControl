import { describe, expect, it } from 'vitest'
import router from '@/router'

describe('P2 product routes', () => {
  it('registers the core product pages', () => {
    const paths = router.getRoutes().map((route) => route.path)
    for (const path of ['/', '/catalog', '/search', '/datasets/:id', '/fields/:id', '/code-tables', '/word-roots', '/metrics', '/overview', '/profile']) {
      expect(paths).toContain(path)
    }
  })
})
