import { describe, expect, it } from 'vitest'
import { MockLanguageModelV3 } from 'ai/test'
import { makeIdSheet, renderSheet, runExactRead, scoreExactRead } from './exact-read.js'

const { ids } = makeIdSheet(1)

describe('makeIdSheet', () => {
    it('is deterministic per seed and differs across seeds', () => {
        expect(makeIdSheet(1)).toEqual(makeIdSheet(1))
        expect(makeIdSheet(2).ids).not.toEqual(ids)
    })
    it('has 20 distinct 12-char ids that all appear in the text', () => {
        const sheet = makeIdSheet(7)
        expect(sheet.ids).toHaveLength(20)
        expect(new Set(sheet.ids).size).toBe(20)
        for (const id of sheet.ids) {
            expect(id).toMatch(/^[a-z0-9]{12}$/)
            expect(sheet.text).toContain(id)
        }
    })
})

describe('renderSheet', () => {
    it('returns one PNG', async () => {
        const png = await renderSheet(makeIdSheet(1).text)
        expect(png.subarray(0, 8).toString('hex')).toBe('89504e470d0a1a0a')
    }, 60_000)
})

describe('scoreExactRead', () => {
    it('scores all exact as 20', () => {
        expect(scoreExactRead(ids, ids.join('\n'))).toEqual({ score: 20, misses: [] })
    })
    it('counts one character off as a miss', () => {
        const bad = ids[0]!.slice(0, 11) + (ids[0]!.endsWith('a') ? 'b' : 'a')
        const r = scoreExactRead(ids, [bad, ...ids.slice(1)].join('\n'))
        expect(r.score).toBe(19)
        expect(r.misses).toEqual([ids[0]])
    })
    it('counts an id cut across two lines as a miss', () => {
        const r = scoreExactRead(ids, [`${ids[0]!.slice(0, 6)}\n${ids[0]!.slice(6)}`, ...ids.slice(1)].join('\n'))
        expect(r.score).toBe(19)
    })
    it('counts an id with a character added as a miss', () => {
        const r = scoreExactRead(ids, [ids[0] + 'x', ...ids.slice(1)].join('\n'))
        expect(r.score).toBe(19)
        expect(r.misses).toEqual([ids[0]])
    })
    it('ignores extra ids and counts a repeat once', () => {
        const r = scoreExactRead(ids, [...ids, ...ids, 'zzzzzzzzzzzz'].join('\n'))
        expect(r.score).toBe(20)
    })
})

describe('runExactRead', () => {
    it('scores a stub model that answers 19 ids as 19', async () => {
        const { ids: sheetIds } = makeIdSheet(3)
        const model = new MockLanguageModelV3({
            doGenerate: async () => ({
                content: [{ type: 'text', text: sheetIds.slice(0, 19).join('\n') }],
                finishReason: { unified: 'stop', raw: 'stop' },
                usage: { inputTokens: { total: 1, noCache: 1, cacheRead: 0, cacheWrite: 0 }, outputTokens: { total: 1, text: 1, reasoning: 0 } },
                warnings: [],
            }),
        })
        const r = await runExactRead({ provider: 'stub', model: 'm', languageModel: model }, 3)
        expect(r).toEqual({ provider: 'stub', model: 'm', score: 19, seed: 3 })
    }, 60_000)
})
