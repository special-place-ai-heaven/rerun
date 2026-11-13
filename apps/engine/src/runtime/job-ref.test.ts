import { describe, expect, it } from 'vitest'
import { parseJobRef } from './job-ref.js'

describe('parseJobRef', () => {
    it.each([
        ['JOB special-place-ai-heaven/rerun#128', 'rerun#128'],
        ['JOB rerun#128', 'rerun#128'],
        ['JOB rerun#128 chunk 2 of the plan\nmore', 'rerun#128'],
        ['JOB owner/repo#7\nbody', 'repo#7'],
    ])('reads %j', (message, jobRef) => {
        expect(parseJobRef(message)).toEqual({ jobRef })
    })

    it.each([
        ['lowercase job', 'job rerun#128'],
        ['JOB on line 2', 'hello\nJOB rerun#128'],
        ['no number', 'JOB rerun#'],
        ['zero', 'JOB rerun#0'],
        ['no repo', 'JOB #12'],
        ['empty', ''],
    ])('rejects %s', (_name, message) => {
        expect(parseJobRef(message)).toBeNull()
    })
})
