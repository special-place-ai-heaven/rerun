import { readFileSync } from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { FACTORY_SNAPSHOT_MAX_BYTES, factorySnapshotSchema } from '@rerun/contracts'

// The picture the delegator pushes each beat. The sample is shared with the delegator's own tests, so
// both sides of the wire hold to one format.
const SAMPLE = path.resolve(import.meta.dirname, '../../../../packages/contracts/fixtures/factory-snapshot.sample.json')
const sample = () => JSON.parse(readFileSync(SAMPLE, 'utf8'))

describe('factorySnapshotSchema', () => {
    it('accepts the shared sample and keeps it under the size cap', () => {
        const text = readFileSync(SAMPLE, 'utf8')
        expect(factorySnapshotSchema.parse(JSON.parse(text)).jobs).toHaveLength(6)
        expect(text.length).toBeLessThan(FACTORY_SNAPSHOT_MAX_BYTES)
    })

    it('refuses a state the ledger does not have', () => {
        const s = sample()
        s.jobs[0].state = 'cancelled'
        expect(factorySnapshotSchema.safeParse(s).success).toBe(false)
    })

    it('refuses fields it does not know, at the top and on a job', () => {
        expect(factorySnapshotSchema.safeParse({ ...sample(), extra: 1 }).success).toBe(false)
        const s = sample()
        s.jobs[0].secret = 'x'
        expect(factorySnapshotSchema.safeParse(s).success).toBe(false)
    })

    it('refuses more than 300 jobs', () => {
        const s = sample()
        s.jobs = Array.from({ length: 301 }, (_, i) => ({ ...s.jobs[0], issue: 1000 + i }))
        expect(factorySnapshotSchema.safeParse(s).success).toBe(false)
    })
})
