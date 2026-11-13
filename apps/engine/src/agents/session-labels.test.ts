import { describe, expect, it } from 'vitest'
import { LABEL_ENV_NAMES, sessionLabels } from './session-labels.js'

const base = { agentId: 'a1', agentName: 'Code', sessionId: 's1' }

describe('sessionLabels', () => {
    it('labels all fields', () => {
        expect(
            sessionLabels({ ...base, runId: 'r1', jobRef: 'rerun#133', branch: 'chunk/133-c1', copyIndex: 2 }),
        ).toEqual({
            RERUN_COWORKER: 'Code',
            RERUN_COWORKER_ID: 'a1',
            RERUN_SESSION_ID: 's1',
            RERUN_RUN_ID: 'r1',
            RERUN_JOB: 'rerun#133',
            RERUN_BRANCH: 'chunk/133-c1',
            RERUN_COPY: '2',
        })
    })

    it('omits a missing job and branch', () => {
        const labels = sessionLabels({ ...base, jobRef: null })
        expect(labels).toEqual({ RERUN_COWORKER: 'Code', RERUN_COWORKER_ID: 'a1', RERUN_SESSION_ID: 's1' })
    })

    it('strips newline and control characters', () => {
        const labels = sessionLabels({ ...base, agentName: 'Co\nde\r\x00\x1b[31m; $(x)' })
        expect(labels.RERUN_COWORKER).toBe('Code31m x')
        expect(labels.RERUN_COWORKER).not.toMatch(/[\n\r\x00\x1b]/)
    })

    it('cuts a 300-char value to 200', () => {
        expect(sessionLabels({ ...base, branch: 'a'.repeat(300) }).RERUN_BRANCH).toHaveLength(200)
    })

    it('omits an empty string', () => {
        const labels = sessionLabels({ ...base, runId: '', branch: '\n' })
        expect(labels).not.toHaveProperty('RERUN_RUN_ID')
        expect(labels).not.toHaveProperty('RERUN_BRANCH')
    })

    it('gives copyIndex as RERUN_COPY, including 0', () => {
        expect(sessionLabels({ ...base, copyIndex: 3 }).RERUN_COPY).toBe('3')
        expect(sessionLabels({ ...base, copyIndex: 0 }).RERUN_COPY).toBe('0')
        expect(LABEL_ENV_NAMES).toContain('RERUN_COPY')
    })
})
