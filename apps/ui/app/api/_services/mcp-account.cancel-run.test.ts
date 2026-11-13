import { workspaceActor } from '@/app/api/_auth/access'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { cancelRun, getRun } from '@/lib/engine/client'
import { ACCOUNT_TOOL_DEFS } from '@/lib/mcp/account-tools'

import { resolveAgentTarget } from './chat.service'
import { dispatchAccountTool } from './mcp-account.service'

vi.mock('@/supabase/serviceRole', () => ({ createServiceRoleClient: vi.fn() }))
vi.mock('@/lib/engine/client')
vi.mock('@/lib/services/registry', () => ({ readRegistry: vi.fn(), connectorSkillOwners: () => new Map() }))
vi.mock('./workspace-engine.service', () => ({ findWorkspaceEngine: vi.fn(), getConnectionForAgent: vi.fn(), getWorkspaceConnection: vi.fn() }))
vi.mock('./agent.service', () => ({ changeAgentHandle: vi.fn(), createAgent: vi.fn(), deleteAgent: vi.fn(), duplicateAgent: vi.fn(), moveAgentToBox: vi.fn(), renameAgent: vi.fn() }))
vi.mock('./agent-setup.service', () => ({ declareService: vi.fn(), installServiceSlugs: vi.fn() }))
vi.mock('./chat.service', () => ({ ensureSessionRow: vi.fn(), resolveAgentTarget: vi.fn() }))
vi.mock('./services.service', () => ({ allocateServiceInstance: vi.fn(), listCatalogServices: vi.fn(), listInstalledServices: vi.fn(), loadManifest: vi.fn(), searchCatalogServices: vi.fn(), toAuthMethodSummaries: vi.fn(() => []), uninstallService: vi.fn() }))
vi.mock('./mcp-shares.service', () => ({ dispatchShareTool: vi.fn() }))

const CONN = { baseUrl: 'https://engine.test', apiKey: null }
const ACTOR = workspaceActor(7)
const run = (status: string) => ({ id: 'run-1', status, output: null, error: null, startedAt: 1, finishedAt: null }) as never

describe('cancel_run account tool', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(resolveAgentTarget).mockResolvedValue({ conn: CONN, engineAgentId: 'engine-own', contentLocked: false } as never)
        vi.mocked(cancelRun).mockResolvedValue(undefined)
    })

    it('cancel_run stops a running run: status cancelled, wasRunning true', async () => {
        vi.mocked(getRun).mockResolvedValueOnce(run('running')).mockResolvedValueOnce(run('cancelled'))
        const out = (await dispatchAccountTool(ACTOR, 'cancel_run', { agentId: 'agent-own', runId: 'run-1' })) as Record<string, unknown>
        expect(cancelRun).toHaveBeenCalledWith(CONN, 'engine-own', 'run-1')
        expect(out).toMatchObject({ status: 'cancelled', wasRunning: true })
    })

    it('cancel_run on an ended run returns its status, wasRunning false, and is not an error', async () => {
        vi.mocked(getRun).mockResolvedValue(run('done'))
        const out = (await dispatchAccountTool(ACTOR, 'cancel_run', { agentId: 'agent-own', runId: 'run-1' })) as Record<string, unknown>
        expect(out).toMatchObject({ status: 'done', wasRunning: false })
    })

    it('cancel_run sends the engine the id resolveAgentTarget returned, not the caller\'s agentId', async () => {
        vi.mocked(getRun).mockResolvedValue(run('running'))
        await dispatchAccountTool(ACTOR, 'cancel_run', { agentId: 'agent-own', runId: 'run-1' })
        expect(vi.mocked(resolveAgentTarget).mock.calls[0][2]).toBe('use')
        for (const fn of [getRun, cancelRun]) for (const call of vi.mocked(fn).mock.calls) expect(call[1]).toBe('engine-own')
    })

    it('cancel_run on an unknown run gives the same error as get_run', async () => {
        vi.mocked(getRun).mockRejectedValue(new Error('Run not found'))
        const viaGet = await dispatchAccountTool(ACTOR, 'get_run', { agentId: 'agent-own', runId: 'nope' }).catch(e => (e as Error).message)
        await expect(dispatchAccountTool(ACTOR, 'cancel_run', { agentId: 'agent-own', runId: 'nope' })).rejects.toThrow(viaGet as string)
        expect(cancelRun).not.toHaveBeenCalled()
    })

    it('is listed with agentId and runId required', () => {
        const tool = ACCOUNT_TOOL_DEFS.find(t => t.name === 'cancel_run') as { inputSchema: { required: string[] } } | undefined
        expect(tool?.inputSchema.required).toEqual(['agentId', 'runId'])
    })
})
