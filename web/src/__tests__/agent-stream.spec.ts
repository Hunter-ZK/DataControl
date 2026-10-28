import { afterEach, describe, expect, it, vi } from 'vitest'
import { AgentTurnCancelledError, streamAgentTurn } from '@/api/client'

const originalFetch = globalThis.fetch
afterEach(() => {
  globalThis.fetch = originalFetch
  localStorage.clear()
})

function chunks(values: string[]) {
  const encoder = new TextEncoder()
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const value of values) controller.enqueue(encoder.encode(value))
      controller.close()
    },
  })
}

describe('Agent NDJSON stream contract', () => {
  it('reassembles UTF-8 chunks and surfaces only actual activity and final answer', async () => {
    const observed: string[] = []
    const data =
      '{"type":"started","runId":"r1"}\n' +
      '{"type":"activity","event":{"type":"tool_call","callId":"x1","tool":"resolve_metric"}}\n' +
      '{"type":"result","result":{"answer":"本期贷款余额","sessionId":"abc","events":[]}}\n'
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      body: chunks([data.slice(0, 18), data.slice(18, 52), data.slice(52)]),
    })) as unknown as typeof fetch
    const result = await streamAgentTurn('question', null, 'r1', e => observed.push(e.type), new AbortController().signal)
    expect(result.answer).toBe('本期贷款余额')
    expect(observed).toEqual(['started', 'activity', 'result'])
  })

  it('sends explicit mode and public-provider consent only for free test', async () => {
    let body: Record<string, unknown> = {}
    globalThis.fetch = vi.fn(async (_url: RequestInfo | URL, init?: RequestInit) => {
      body = JSON.parse(String(init?.body)) as Record<string, unknown>
      return {
        ok: true,
        body: chunks(['{"type":"result","result":{"answer":"模拟结果","sqlExecuted":false,"hiddenReasoningExposed":false}}\n']),
      }
    }) as unknown as typeof fetch
    await streamAgentTurn('synthetic question', null, 'r-free', () => {}, new AbortController().signal, 'free-test')
    expect(body.modelMode).toBe('free-test')
    expect(body.publicGatewayConsent).toBe(true)
    await streamAgentTurn('synthetic question', null, 'r-official', () => {}, new AbortController().signal)
    expect(body.modelMode).toBe('deepseek')
    expect(body.publicGatewayConsent).toBe(false)
  })

  it('never fabricates a completed response after cancellation', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      body: chunks(['{"type":"cancelled"}\n']),
    })) as unknown as typeof fetch
    await expect(streamAgentTurn('question', null, 'r2', () => {}, new AbortController().signal))
      .rejects.toBeInstanceOf(AgentTurnCancelledError)
  })

  it('rejects incomplete streams instead of showing a false answer', async () => {
    globalThis.fetch = vi.fn(async () => ({
      ok: true,
      body: chunks(['{"type":"started","runId":"r3"}\n']),
    })) as unknown as typeof fetch
    await expect(streamAgentTurn('question', null, 'r3', () => {}, new AbortController().signal))
      .rejects.toThrow('without a final result')
  })
})
