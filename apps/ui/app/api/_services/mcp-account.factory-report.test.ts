import { workspaceActor } from '@/app/api/_auth/access'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getFactorySnapshot } from '@/lib/factory/snapshot-store'
import { ACCOUNT_TOOL_DEFS } from '@/lib/mcp/account-tools'

import { dispatchAccountTool } from './mcp-account.service'

vi.mock('server-only', () => ({}))
vi.mock('@/supabase/serviceRole', () => ({ createServiceRoleClient: vi.fn() }))
vi.mock('@/lib/engine/client')
vi.mock('@/lib/services/registry', () => ({ readRegistry: vi.fn(), connectorSkillOwners: () => new Map() }))
vi.mock('./workspace-engine.service', () => ({ findWorkspaceEngine: vi.fn(), getConnectionForAgent: vi.fn(), getWorkspaceConnection: vi.fn() }))
vi.mock('./agent.service', () => ({ changeAgentHandle: vi.fn(), createAgent: vi.fn(), deleteAgent: vi.fn(), duplicateAgent: vi.fn(), moveAgentToBox: vi.fn(), renameAgent: vi.fn() }))
vi.mock('./agent-setup.service', () => ({ declareService: vi.fn(), installServiceSlugs: vi.fn() }))
vi.mock('./chat.service', () => ({ ensureSessionRow: vi.fn(), resolveAgentTarget: vi.fn() }))
vi.mock('./services.service', () => ({ allocateServiceInstance: vi.fn(), listCatalogServices: vi.fn(), listInstalledServices: vi.fn(), loadManifest: vi.fn(), searchCatalogServices: vi.fn(), toAuthMethodSummaries: vi.fn(() => []), uninstallService: vi.fn() }))
vi.mock('./mcp-shares.service', () => ({ dispatchShareTool: vi.fn() }))

const snap = (madeAt: string, beat = 1, extra: Record<string, unknown> = {}) => ({
    version: 1, madeAt, beat, repo: 'a/b', jobs: [], holds: [], pools: [],
    endedToday: { merged: 0, rejected: 0, blocked: 0, failed: 0, returned: 0 }, ...extra,
})

describe('factory_report account tool', () => {
    beforeEach(() => vi.clearAllMocks())

    it('is listed with a description of 40 characters or more', () => {
        const def = ACCOUNT_TOOL_DEFS.find(t => t.name === 'factory_report')
        expect(def).toBeTruthy()
        expect(def!.description.length).toBeGreaterThanOrEqual(40)
    })

    it('keeps the picture for the caller\'s workspace only', async () => {
        const s = snap('2026-11-14T06:00:00Z', 5)
        expect(await dispatchAccountTool(workspaceActor(101), 'factory_report', { snapshot: s })).toEqual({ kept: true })
        expect(getFactorySnapshot(101)?.snapshot).toEqual(s)
        expect(getFactorySnapshot(102)).toBeNull()
    })

    it('answers kept false for a late older picture and keeps the newer one', async () => {
        const actor = workspaceActor(103)
        await dispatchAccountTool(actor, 'factory_report', { snapshot: snap('2026-11-14T06:00:00Z', 9) })
        expect(await dispatchAccountTool(actor, 'factory_report', { snapshot: snap('2026-11-14T05:00:00Z', 1) })).toEqual({ kept: false })
        expect(getFactorySnapshot(103)?.snapshot.beat).toBe(9)
    })

    it('rejects a snapshot over the size cap before validating it', async () => {
        const big = snap('2026-11-14T06:00:00Z', 1, { junk: 'x'.repeat(300 * 1024) })
        await expect(dispatchAccountTool(workspaceActor(104), 'factory_report', { snapshot: big })).rejects.toThrow(/factory_report: the snapshot is over \d+ bytes/)
        expect(getFactorySnapshot(104)).toBeNull()
    })

    it('rejects a snapshot that does not match the schema, without echoing it', async () => {
        const err = await dispatchAccountTool(workspaceActor(105), 'factory_report', { snapshot: { version: 1, secret: 'topsecret' } }).catch(e => e as Error)
        expect((err as Error).message).toBe('factory_report: the snapshot does not match the schema')
        await expect(dispatchAccountTool(workspaceActor(105), 'factory_report', {})).rejects.toThrow(/does not match the schema/)
        expect(getFactorySnapshot(105)).toBeNull()
    })
})
