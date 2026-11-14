import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({ requireWorkspaceId: vi.fn(), getFactorySnapshot: vi.fn() }))

vi.mock('@/app/api/_auth/ownership', () => ({ requireWorkspaceId: mocks.requireWorkspaceId }))
vi.mock('@/lib/factory/snapshot-store', () => ({ getFactorySnapshot: mocks.getFactorySnapshot }))

const { readFactorySnapshotAction } = await import('./factory.actions')

const SNAPSHOT = { madeAt: '2026-11-14T06:00:00.000Z', beat: 3 }

beforeEach(() => {
    vi.clearAllMocks()
    mocks.requireWorkspaceId.mockResolvedValue(7)
    mocks.getFactorySnapshot.mockReturnValue(null)
})

afterEach(() => {
    vi.useRealTimers()
})

describe('readFactorySnapshotAction', () => {
    it('reads the picture of the signed-in workspace, not of an argument', async () => {
        await (readFactorySnapshotAction as (...args: unknown[]) => Promise<unknown>)(99)

        expect(mocks.getFactorySnapshot).toHaveBeenCalledWith(7)
    })

    it('answers null when no picture is stored', async () => {
        await expect(readFactorySnapshotAction()).resolves.toBeNull()
    })

    it('answers the snapshot, when it was received and its age', async () => {
        vi.useFakeTimers()
        vi.setSystemTime(new Date('2026-11-14T06:10:00.000Z'))
        const receivedAt = Date.parse('2026-11-14T06:09:30.000Z')
        mocks.getFactorySnapshot.mockReturnValue({ snapshot: SNAPSHOT, receivedAt })

        await expect(readFactorySnapshotAction()).resolves.toEqual({ snapshot: SNAPSHOT, receivedAt, ageMs: 30_000 })
    })

    it('refuses when signed out: the store is not read', async () => {
        mocks.requireWorkspaceId.mockRejectedValue(new Error('unauthenticated'))

        await expect(readFactorySnapshotAction()).rejects.toThrow('unauthenticated')
        expect(mocks.getFactorySnapshot).not.toHaveBeenCalled()
    })
})
