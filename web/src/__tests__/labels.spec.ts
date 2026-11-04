import { describe, expect, it } from 'vitest'
import { assetTypeLabel, statusLabel } from '@/utils/labels'

describe('UI labels', () => {
  it('maps lifecycle values to Chinese labels', () => {
    expect(statusLabel('ONLINE')).toBe('在用')
    expect(statusLabel('VALID')).toBe('有效')
    expect(statusLabel('OFFLINE')).toBe('已下线')
    expect(statusLabel('DEPRECATED')).toBe('已废弃')
    expect(statusLabel('DRAFT')).toBe('草稿')
  })

  it('keeps unknown lifecycle values visible', () => {
    expect(statusLabel('CUSTOM_STATE')).toBe('CUSTOM_STATE')
  })

  it('maps asset types to Chinese labels', () => {
    expect(assetTypeLabel('TABLE')).toBe('数据集')
    expect(assetTypeLabel('COLUMN')).toBe('字段')
    expect(assetTypeLabel('CODE_TABLE')).toBe('码表')
  })
})
