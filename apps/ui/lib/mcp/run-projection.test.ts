import { describe, expect, it } from 'vitest'
import { projectRun } from './run-projection'

const base = { id: 'r1', status: 'done', sessionId: 's1', provider: null, model: null, triggerSource: 'api', triggerSlug: null, stepCount: 1, inputTokens: null, outputTokens: null, totalTokens: null, costMicros: null, startedAt: '2026-11-13T00:00:00.000Z', finishedAt: null, error: null }

describe('projectRun goal', () => {
    it('returns the goal of the run unchanged', () => {
        const goal = { lastLineForms: [{ prefix: 'PR: ', rest: 'pull-url' as const }], turnLimit: 3, state: 'met' as const, verdicts: [{ turn: 1, met: true, reason: 'ok' }] }
        expect(projectRun({ ...base, goal }).goal).toEqual(goal)
    })

    it('returns null for a run without a goal', () => {
        expect(projectRun(base).goal).toBeNull()
        expect(projectRun({ ...base, goal: null }).goal).toBeNull()
    })
})
