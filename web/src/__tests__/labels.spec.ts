import { describe, expect, it } from 'vitest'
import { assetTypeLabel, statusLabel } from '@/utils/labels'

describe('presentation labels', () => {
  it('maps lifecycle states without altering unknown technical states', () => {
    expect(statusLabel('ONLINE')).toBe('在用')
    expect(statusLabel('EFFECTIVE')).toBe('有效')
    expect(statusLabel('OFFLINE')).toBe('已下线')
    expect(statusLabel('DRAFT')).toBe('草稿')
    expect(statusLabel('CUSTOM_STATE')).toBe('CUSTOM_STATE')
  })
  it('presents reference asset types in Chinese', () => {
    expect(assetTypeLabel('CODE_TABLE')).toBe('码表')
    expect(assetTypeLabel('STAT_SYSTEM')).toBe('统计制度')
  })
})
