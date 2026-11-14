import 'server-only'

import type { FactorySnapshot } from '@rerun/contracts'

// The newest picture of the factory line per workspace, as the delegator pushes it each beat
// (FactorySnapshot, packages/contracts/src/factory-snapshot.ts). Kept in the memory of the app's one
// server process (`next start` in one container, deploy/vps); on a restart the next beat refills it
// within a beat. Held on globalThis so a dev reload of this module keeps what was pushed.
// The writer is the account tool that receives the push; the reader is the factory page's read.

export type HeldSnapshot = { snapshot: FactorySnapshot; receivedAt: number }

const store = globalThis as typeof globalThis & { __rerunFactorySnapshots?: Map<number, HeldSnapshot> }
const held = (store.__rerunFactorySnapshots ??= new Map<number, HeldSnapshot>())

// Keeps the picture unless an older one arrives late: the newest by `madeAt` wins, never by `beat`,
// which starts again at 0 when the delegator restarts. Returns whether it was kept.
export function putFactorySnapshot(workspaceId: number, snapshot: FactorySnapshot, receivedAt = Date.now()): boolean {
    const current = held.get(workspaceId)
    if (current && Date.parse(current.snapshot.madeAt) > Date.parse(snapshot.madeAt)) return false
    held.set(workspaceId, { snapshot, receivedAt })
    return true
}

export function getFactorySnapshot(workspaceId: number): HeldSnapshot | null {
    return held.get(workspaceId) ?? null
}
