import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { vi } from 'vitest'

process.env.RERUN_DATA_DIR = mkdtempSync(resolve(tmpdir(), 'rerun-goal-'))
process.env.RERUN_API_KEY = ''

const state = vi.hoisted(() => ({ answer: 'ok', provider: 'custom', options: undefined as undefined | { goal?: { goal: unknown; record: (v: unknown) => Promise<void> } } }))

vi.mock('../tools/registry.js', () => ({ buildTools: async () => ({ tools: {}, close: async () => {} }) }))

vi.mock('../agents/providers.js', async importOriginal => {
    const actual = await importOriginal<typeof import('../agents/providers.js')>()
    const { MockLanguageModelV3 } = await import('ai/test')
    return {
        ...actual,
        resolveModel: (...args: unknown[]) => {
            state.options = args[4] as typeof state.options
            return {
                model: new MockLanguageModelV3({
                    doStream: async () => ({
                        stream: new ReadableStream({
                            start(controller) {
                                for (const part of [
                                    { type: 'stream-start', warnings: [] },
                                    { type: 'text-start', id: '0' },
                                    { type: 'text-delta', id: '0', delta: state.answer },
                                    { type: 'text-end', id: '0' },
                                    { type: 'finish', finishReason: { unified: 'stop' }, usage: { inputTokens: 1, outputTokens: 1, totalTokens: 2 } },
                                ])
                                    controller.enqueue(part)
                                controller.close()
                            },
                        }),
                    }),
                }),
                close: async () => {},
            }
        },
    }
})

vi.mock('../agents/availability.js', async importOriginal => {
    const actual = await importOriginal<typeof import('../agents/availability.js')>()
    return {
        ...actual,
        resolveRunModel: async (agent: { resolved: Record<string, unknown> }) => ({ ...agent.resolved, provider: state.provider }),
    }
})

const { beforeAll, describe, expect, it } = await import('vitest')
const { mkdir } = await import('node:fs/promises')
const { migrate } = await import('../db/migrate.js')
const { agentConfigSchema } = await import('../agents/types.js')
const { writeAgentConfig } = await import('../agents/config-write.js')
const { agentDir } = await import('../config/paths.js')
const { getAgent } = await import('../agents/registry.js')
const { createSession } = await import('../db/repos/sessions.js')
const { runAgent } = await import('./loop.js')
const { chatRoutes } = await import('../http/routes/chat.js')
const { runRoutes } = await import('../http/routes/runs.js')
const { Hono } = await import('hono')

const id = 'goalagent'
const goal = { lastLineForms: [{ prefix: 'PR: ', rest: 'pull-url' as const }], turnLimit: 3 }

async function runWith(answer: string, withGoal: boolean) {
    state.answer = answer
    const session = await createSession(id, 'go')
    const agent = await getAgent(id)
    const run = await runAgent(agent, session.id, 'go', undefined, undefined, undefined, { source: 'chat', ...(withGoal ? { goal } : {}) })
    await run.settled
    const app = new Hono().route('/agents/:id/runs', runRoutes)
    const res = await app.request(`/agents/${id}/runs/${run.runId}`)
    return (await res.json()) as { status: string; goal: { state: string; verdicts: { turn: number; met: boolean; reason: string }[] } | null }
}

describe('run goal', () => {
    beforeAll(async () => {
        await migrate()
        await mkdir(agentDir(id), { recursive: true })
        await writeAgentConfig(id, agentConfigSchema.parse({ name: 'goal' }))
    })

    it('answers 400 invalid_goal and starts no run', async () => {
        const app = new Hono().route('/agents/:id', chatRoutes)
        for (const bad of [{ ...goal, turnLimit: 0 }, { ...goal, extra: 1 }]) {
            const res = await app.request(`/agents/${id}/chat`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ message: 'hi', goal: bad }) })
            expect(res.status).toBe(400)
            expect(await res.json()).toEqual({ error: 'invalid_goal' })
        }
        const list = await new Hono().route('/agents/:id/runs', runRoutes).request(`/agents/${id}/runs`)
        expect(JSON.stringify(await list.json())).not.toContain('"id"')
    })

    it('meets the goal on a pull request url', async () => {
        const r = await runWith('work\nPR: https://github.com/o/r/pull/5', true)
        expect(r.status).toBe('done')
        expect(r.goal?.state).toBe('met')
        expect(r.goal?.verdicts).toHaveLength(1)
        expect(r.goal?.verdicts[0]?.turn).toBe(1)
    })

    it('does not meet it when another line comes last, and quotes that line', async () => {
        const r = await runWith('PR: https://github.com/o/r/pull/5\nTools: shell 3 calls', true)
        expect(r.status).toBe('done')
        expect(r.goal?.state).toBe('not_met')
        expect(r.goal?.verdicts[0]?.reason).toContain('Tools: shell 3 calls')
    })

    it('reads goal null for a run without one', async () => {
        const r = await runWith('plain', false)
        expect(r.goal).toBeNull()
    })

    it('hands a Claude run the goal and a record that writes to the row', async () => {
        state.provider = 'claude'
        try {
            await runWith('x', true)
            const opt = state.options?.goal
            expect(opt?.goal).toEqual(goal)
            expect(typeof opt?.record).toBe('function')
        } finally {
            state.provider = 'custom'
        }
    })
})
