import { describe, expect, it, vi } from 'vitest'
import { abortRun, syncAgentStatus, activeRunCount, agentHasLiveRun, claimSession, registerRunAbort, releaseSession, sessionClaim, sessionClaimCount, setRunCancel, unregisterRunAbort } from './run-control.js'

const setAgentStatus = vi.hoisted(() => vi.fn(async (_id: string, _status: string) => {}))
vi.mock('../db/repos/agents.js', () => ({ setAgentStatus }))

describe('abortRun', () => {
    it('returns false for a run it never registered', () => {
        expect(abortRun('ghost')).toBe(false)
    })

    it('aborts the signal, runs the cancel hook, frees the claim and forgets the run', () => {
        const before = activeRunCount()
        const controller = registerRunAbort('run-a', 'agent-1')
        const cancel = vi.fn()
        setRunCancel('run-a', cancel)
        expect(claimSession('sess-a', 'run-a')).toBeNull()
        expect(activeRunCount()).toBe(before + 1)

        expect(abortRun('run-a')).toBe(true)

        expect(controller.signal.aborted).toBe(true)
        expect(cancel).toHaveBeenCalledTimes(1)
        expect(sessionClaim('sess-a')).toBeNull()
        expect(activeRunCount()).toBe(before)
    })

    it('reports false on a second abort and does not cancel twice', () => {
        registerRunAbort('run-b', 'agent-1')
        const cancel = vi.fn()
        setRunCancel('run-b', cancel)

        expect(abortRun('run-b')).toBe(true)
        expect(abortRun('run-b')).toBe(false)
        expect(cancel).toHaveBeenCalledTimes(1)
    })

    it('aborts a run that never set a cancel hook', () => {
        const controller = registerRunAbort('run-c', 'agent-1')
        expect(abortRun('run-c')).toBe(true)
        expect(controller.signal.aborted).toBe(true)
    })
})

describe('setRunCancel', () => {
    it('ignores a run that is not registered', () => {
        const cancel = vi.fn()
        setRunCancel('not-registered', cancel)
        registerRunAbort('not-registered', 'agent-1')
        abortRun('not-registered')
        expect(cancel).not.toHaveBeenCalled()
    })
})

describe('session claims', () => {
    it('does nothing when releasing a run that holds no claim', () => {
        claimSession('sess-held', 'holder')
        const count = sessionClaimCount()

        releaseSession('no-claim')

        expect(sessionClaimCount()).toBe(count)
        expect(sessionClaim('sess-held')?.runId).toBe('holder')
        releaseSession('holder')
    })

    it('records who holds a session and since when', () => {
        const before = Date.now()
        claimSession('sess-time', 'run-t')

        const claim = sessionClaim('sess-time')

        expect(claim?.runId).toBe('run-t')
        expect(claim?.claimedAt).toBeGreaterThanOrEqual(before)
        expect(claim?.claimedAt).toBeLessThanOrEqual(Date.now())
        releaseSession('run-t')
        expect(sessionClaim('sess-time')).toBeNull()
    })

    it('counts claimed sessions', () => {
        const before = sessionClaimCount()
        claimSession('sess-1', 'r1')
        claimSession('sess-2', 'r2')
        claimSession('sess-2', 'r3')

        expect(sessionClaimCount()).toBe(before + 2)

        releaseSession('r1')
        releaseSession('r2')
        expect(sessionClaimCount()).toBe(before)
    })

    it('keeps the holder claim when a refused run releases', () => {
        claimSession('sess-x', 'holder-x')
        expect(claimSession('sess-x', 'refused')).toBe('holder-x')

        releaseSession('refused')

        expect(sessionClaim('sess-x')?.runId).toBe('holder-x')
        releaseSession('holder-x')
    })

    it('unregistering a run frees its claim and drops it from the active count', () => {
        const before = activeRunCount()
        registerRunAbort('run-u', 'agent-1')
        claimSession('sess-u', 'run-u')

        unregisterRunAbort('run-u')

        expect(activeRunCount()).toBe(before)
        expect(sessionClaim('sess-u')).toBeNull()
        expect(abortRun('run-u')).toBe(false)
    })

    it('knows which coworkers have a run live, until it ends or is aborted', () => {
        registerRunAbort('live-1', 'coworker')
        registerRunAbort('live-2', 'coworker')
        expect(agentHasLiveRun('coworker')).toBe(true)
        expect(agentHasLiveRun('someone-else')).toBe(false)

        unregisterRunAbort('live-1')
        expect(agentHasLiveRun('coworker')).toBe(true)
        abortRun('live-2')
        expect(agentHasLiveRun('coworker')).toBe(false)
    })

    it('remembers who started the run holding a conversation', () => {
        claimSession('sess-author', 'run-author', 'u1')
        expect(sessionClaim('sess-author')?.authorId).toBe('u1')
        releaseSession('run-author')
        claimSession('sess-author', 'run-unsigned')
        expect(sessionClaim('sess-author')?.authorId).toBeUndefined()
        releaseSession('run-unsigned')
    })
})

describe('syncAgentStatus', () => {
    it('stays busy while any run of the coworker is live, idle once the last one settles', async () => {
        registerRunAbort('sync-1', 'sync-agent')
        registerRunAbort('sync-2', 'sync-agent')

        unregisterRunAbort('sync-1')
        await syncAgentStatus('sync-agent')
        expect(setAgentStatus).toHaveBeenLastCalledWith('sync-agent', 'busy')

        unregisterRunAbort('sync-2')
        await syncAgentStatus('sync-agent')
        expect(setAgentStatus).toHaveBeenLastCalledWith('sync-agent', 'idle')
    })
})
