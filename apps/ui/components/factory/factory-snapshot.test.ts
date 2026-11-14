import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { FACTORY_SNAPSHOT_MAX_BYTES, factoryJobStateSchema, factorySnapshotSchema } from '@rerun/contracts'

// The picture the delegator pushes each beat. The sample in packages/contracts/fixtures is the one
// the delegator's own report is to be tested against too.
const ROOT = path.resolve(import.meta.dirname, '../../../..')
const SAMPLE = path.join(ROOT, 'packages/contracts/fixtures/factory-snapshot.sample.json')
const sample = () => JSON.parse(readFileSync(SAMPLE, 'utf8'))
type Sample = ReturnType<typeof sample>

describe('factorySnapshotSchema', () => {
    it('accepts the shared sample and keeps it under the byte cap', () => {
        const text = readFileSync(SAMPLE, 'utf8')
        expect(factorySnapshotSchema.parse(JSON.parse(text)).jobs).toHaveLength(6)
        expect(Buffer.byteLength(text, 'utf8')).toBeLessThan(FACTORY_SNAPSHOT_MAX_BYTES)
    })

    it('holds the same job states as the delegator ledger', () => {
        const store = readFileSync(path.join(ROOT, 'tools/factory/store.py'), 'utf8')
        const block = store.match(/JOB_STATES = \(([\s\S]*?)\)/)
        expect(block).not.toBeNull()
        const states = [...block![1].matchAll(/"([a-z_]+)"/g)].map(m => m[1])
        expect(states).toEqual(factoryJobStateSchema.options)
    })

    it('refuses a state the ledger does not have', () => {
        const s = sample()
        s.jobs[0].state = 'cancelled'
        expect(factorySnapshotSchema.safeParse(s).success).toBe(false)
    })

    it('refuses fields it does not know, at every level', () => {
        expect(factorySnapshotSchema.safeParse({ ...sample(), extra: 1 }).success).toBe(false)
        for (const poke of [
            (s: Sample) => { s.jobs[0].secret = 'x' },
            (s: Sample) => { s.holds[0].x = 1 },
            (s: Sample) => { s.pools[0].coworkers[0].x = 1 },
            (s: Sample) => { s.endedToday.x = 1 },
        ]) {
            const s = sample()
            poke(s)
            expect(factorySnapshotSchema.safeParse(s).success).toBe(false)
        }
    })

    it('refuses an over-long title, a time with no offset or an endless time, and more than 300 jobs', () => {
        const long = sample()
        long.jobs[0].title = 'x'.repeat(257)
        expect(factorySnapshotSchema.safeParse(long).success).toBe(false)
        const ok = sample()
        ok.jobs[0].title = 'x'.repeat(256)
        expect(factorySnapshotSchema.safeParse(ok).success).toBe(true)
        const noOffset = sample()
        noOffset.madeAt = '2026-11-14T03:24:30'
        expect(factorySnapshotSchema.safeParse(noOffset).success).toBe(false)
        const endless = sample()
        endless.madeAt = `2026-11-14T03:24:30.${'1'.repeat(100)}Z`
        expect(factorySnapshotSchema.safeParse(endless).success).toBe(false)
        const many = sample()
        many.jobs = Array.from({ length: 301 }, (_, i) => ({ ...many.jobs[0], issue: 1000 + i }))
        expect(factorySnapshotSchema.safeParse(many).success).toBe(false)
    })
})
