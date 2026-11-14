'use server'

import type { FactorySnapshot } from '@rerun/contracts'
import { requireWorkspaceId } from '@/app/api/_auth/ownership'
import { getFactorySnapshot } from '@/lib/factory/snapshot-store'

// The newest factory picture of the signed-in workspace, with when it arrived and how old it is.
// The workspace comes from the session, never from an argument.
export async function readFactorySnapshotAction(): Promise<{ snapshot: FactorySnapshot; receivedAt: number; ageMs: number } | null> {
    const workspaceId = await requireWorkspaceId()
    const held = getFactorySnapshot(workspaceId)
    if (!held) return null
    return { snapshot: held.snapshot, receivedAt: held.receivedAt, ageMs: Date.now() - held.receivedAt }
}
