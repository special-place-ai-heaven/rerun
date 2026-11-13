import { workspaceActor } from '@/app/api/_auth/access'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { listSkills, setSkillEnabled } from '@/lib/engine/client'
import { ACCOUNT_TOOL_DEFS } from '@/lib/mcp/account-tools'
import { readRegistry } from '@/lib/services/registry'

import { resolveAgentTarget } from './chat.service'
import { dispatchAccountTool } from './mcp-account.service'

vi.mock('@/supabase/serviceRole', () => ({ createServiceRoleClient: vi.fn() }))
vi.mock('@/lib/engine/client')
vi.mock('@/lib/services/registry', () => ({ readRegistry: vi.fn(), connectorSkillOwners: (reg: { owners?: Record<string, string> }) => new Map(Object.entries(reg.owners ?? {})) }))
vi.mock('./workspace-engine.service', () => ({ findWorkspaceEngine: vi.fn(), getConnectionForAgent: vi.fn(), getWorkspaceConnection: vi.fn() }))
vi.mock('./agent.service', () => ({ changeAgentHandle: vi.fn(), createAgent: vi.fn(), deleteAgent: vi.fn(), duplicateAgent: vi.fn(), moveAgentToBox: vi.fn(), renameAgent: vi.fn() }))
vi.mock('./agent-setup.service', () => ({ declareService: vi.fn(), installServiceSlugs: vi.fn() }))
vi.mock('./chat.service', () => ({ ensureSessionRow: vi.fn(), resolveAgentTarget: vi.fn() }))
vi.mock('./services.service', () => ({ allocateServiceInstance: vi.fn(), listCatalogServices: vi.fn(), listInstalledServices: vi.fn(), loadManifest: vi.fn(), searchCatalogServices: vi.fn(), toAuthMethodSummaries: vi.fn(() => []), uninstallService: vi.fn() }))
vi.mock('./mcp-shares.service', () => ({ dispatchShareTool: vi.fn() }))

const CONN = { baseUrl: 'https://engine.test', apiKey: null }
const ACTOR = workspaceActor(7)

describe('skill switch through the account tools', () => {
    beforeEach(() => {
        vi.clearAllMocks()
        vi.mocked(resolveAgentTarget).mockResolvedValue({ conn: CONN, engineAgentId: 'engine-own', contentLocked: false } as never)
        vi.mocked(readRegistry).mockResolvedValue({ owners: { 'gmail-skill': 'gmail' } } as never)
    })

    it('list_skills reports enabled, defaulting to true, and keeps readOnly and connector', async () => {
        vi.mocked(listSkills).mockResolvedValue([
            { slug: 'off', name: 'Off', description: 'd', body: '', files: [], enabled: false },
            { slug: 'plain', name: 'Plain', description: 'd', body: '', files: [] },
            { slug: 'gmail-skill', name: 'Gmail', description: 'd', body: '', files: [], enabled: true },
        ] as never)

        const { skills } = (await dispatchAccountTool(ACTOR, 'list_skills', { agentId: 'agent-own' })) as { skills: Record<string, unknown>[] }

        expect(skills.find(s => s.slug === 'off')?.enabled).toBe(false)
        expect(skills.find(s => s.slug === 'plain')?.enabled).toBe(true)
        expect(skills.find(s => s.slug === 'gmail-skill')).toMatchObject({ enabled: true, readOnly: true, connector: 'gmail' })
    })

    it('set_skill_enabled switches an app skill off', async () => {
        vi.mocked(setSkillEnabled).mockResolvedValue({ slug: 'gmail-skill', enabled: false })

        const out = await dispatchAccountTool(ACTOR, 'set_skill_enabled', { agentId: 'agent-own', slug: 'gmail-skill', enabled: false })

        expect(setSkillEnabled).toHaveBeenCalledWith(CONN, 'engine-own', 'gmail-skill', false)
        expect(vi.mocked(resolveAgentTarget).mock.calls[0][2]).toBe('manage')
        expect(out).toEqual({ slug: 'gmail-skill', enabled: false })
    })

    it('refuses a caller without manage access, without calling the client', async () => {
        vi.mocked(resolveAgentTarget).mockRejectedValue(new Error('Coworker not found'))

        await expect(dispatchAccountTool(ACTOR, 'set_skill_enabled', { agentId: 'agent-own', slug: 'x', enabled: true })).rejects.toThrow('Coworker not found')
        expect(setSkillEnabled).not.toHaveBeenCalled()
    })

    it('refuses a missing or non-boolean enabled', async () => {
        await expect(dispatchAccountTool(ACTOR, 'set_skill_enabled', { agentId: 'agent-own', slug: 'x' })).rejects.toThrow(/enabled/)
        await expect(dispatchAccountTool(ACTOR, 'set_skill_enabled', { agentId: 'agent-own', slug: 'x', enabled: 'no' })).rejects.toThrow(/enabled/)
        expect(setSkillEnabled).not.toHaveBeenCalled()
    })

    it('lists set_skill_enabled with its three required fields', () => {
        const tool = ACCOUNT_TOOL_DEFS.find(t => t.name === 'set_skill_enabled') as { inputSchema: { required: string[] } } | undefined
        expect(tool?.inputSchema.required).toEqual(['agentId', 'slug', 'enabled'])
    })
})
