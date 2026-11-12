import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createLiveCounter } from './live-counter.js'

beforeEach(() => {
    vi.useFakeTimers()
})
afterEach(() => {
    vi.useRealTimers()
})

describe('live counter', () => {
    it('100 tool calls within 1 s cause at most one flush', async () => {
        const flush = vi.fn().mockResolvedValue(undefined)
        const counter = createLiveCounter({ flush, minIntervalMs: 2000 })
        for (let i = 0; i < 100; i++) {
            counter.addToolCall()
            await vi.advanceTimersByTimeAsync(10)
        }
        expect(flush.mock.calls.length).toBeLessThanOrEqual(1)
        await vi.advanceTimersByTimeAsync(2000)
        expect(flush.mock.calls.length).toBeLessThanOrEqual(2)
        expect(flush).toHaveBeenLastCalledWith({ toolCalls: 100 })
        counter.dispose()
    })

    it('flushNow always flushes the latest snapshot', async () => {
        const flush = vi.fn().mockResolvedValue(undefined)
        const counter = createLiveCounter({ flush, minIntervalMs: 2000 })
        counter.addToolCall()
        counter.addToolCall()
        counter.setUsage({ inputTokens: 7 })
        counter.setUsage({ outputTokens: 3 })
        await counter.flushNow()
        expect(flush).toHaveBeenLastCalledWith({ toolCalls: 2, usage: { inputTokens: 7, outputTokens: 3 } })
        expect(counter.snapshot()).toEqual({ toolCalls: 2, usage: { inputTokens: 7, outputTokens: 3 } })
        counter.addToolCall()
        await counter.flushNow()
        expect(flush).toHaveBeenLastCalledWith(expect.objectContaining({ toolCalls: 3 }))
        counter.dispose()
    })

    it('a rejecting or throwing flush does not throw into the caller', async () => {
        const rejecting = createLiveCounter({ flush: () => Promise.reject(new Error('db')), minIntervalMs: 10 })
        rejecting.addToolCall()
        await expect(rejecting.flushNow()).resolves.toBeUndefined()
        await vi.advanceTimersByTimeAsync(50)
        rejecting.dispose()
        const throwing = createLiveCounter({ flush: () => { throw new Error('sync') }, minIntervalMs: 10 })
        expect(() => throwing.addToolCall()).not.toThrow()
        await expect(throwing.flushNow()).resolves.toBeUndefined()
        throwing.dispose()
    })

    it('dispose leaves no pending timer and stops further flushes', async () => {
        const flush = vi.fn().mockResolvedValue(undefined)
        const counter = createLiveCounter({ flush, minIntervalMs: 2000 })
        counter.addToolCall()
        counter.addToolCall()
        expect(vi.getTimerCount()).toBe(1)
        counter.dispose()
        expect(vi.getTimerCount()).toBe(0)
        counter.addToolCall()
        await vi.advanceTimersByTimeAsync(5000)
        expect(vi.getTimerCount()).toBe(0)
        expect(flush.mock.calls.length).toBeLessThanOrEqual(1)
    })
})
