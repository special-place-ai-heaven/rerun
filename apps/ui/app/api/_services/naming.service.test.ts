import { beforeEach, describe, expect, it, vi } from 'vitest'

import { blobUrl } from '@/lib/blobs/catalog'
import { faviconUrl } from '@/lib/onboarding/site-favicon'
import { fakeSupabase, type FakeSupabase } from '@/test/supabase-fake'

const WORKSPACE_ID = 7
const FOUNDER = 'user-1'
const COMPANY = { company_name: 'Acme', company_url: 'https://acme.com' }

let service: FakeSupabase
vi.mock('@/supabase/serviceRole', () => ({ createServiceRoleClient: () => service.client }))
vi.mock('@/supabase/session/getServerSession', () => ({ getServerSession: async () => ({ session: null }) }))
vi.mock('@/app/api/_auth/ownership', () => ({ workspaceFounderUserId: async () => FOUNDER }))
const findSiteIcon = vi.hoisted(() => vi.fn())
vi.mock('@/lib/onboarding/site-icon.server', () => ({ findSiteIcon }))

const { ensureWorkspaceNamed } = await import('./naming.service')

function workspaceWithIcon(iconUrl: string | null) {
    service = fakeSupabase(table => {
        if (table === 'workspaces') return { data: { id: WORKSPACE_ID, name: 'My workspace', icon_url: iconUrl, is_sandbox: false } }
        if (table === 'workspace_onboarding') return { data: { answers: COMPANY } }
        return undefined
    })
}

const iconWritten = () => (service.writes('workspaces')[0]?.payload as { icon_url?: string } | undefined)?.icon_url

beforeEach(() => {
    findSiteIcon.mockReset()
    findSiteIcon.mockResolvedValue({ bytes: new Uint8Array([0x89, 0x50, 0x4e, 0x47]), contentType: 'image/png' })
})

describe('ensureWorkspaceNamed and the company favicon', () => {
    it('gives the favicon to a workspace with no icon', async () => {
        workspaceWithIcon(null)

        await ensureWorkspaceNamed({ workspaceId: WORKSPACE_ID, userId: FOUNDER })

        expect(iconWritten()).toBe(faviconUrl('acme.com'))
    })

    it('replaces an illustration nobody picked', async () => {
        workspaceWithIcon(blobUrl('green-energy-blob.webp'))

        await ensureWorkspaceNamed({ workspaceId: WORKSPACE_ID, userId: FOUNDER })

        expect(iconWritten()).toBe(faviconUrl('acme.com'))
    })

    it('leaves the icon alone when the site has none', async () => {
        workspaceWithIcon(null)
        findSiteIcon.mockResolvedValue(null)

        await ensureWorkspaceNamed({ workspaceId: WORKSPACE_ID, userId: FOUNDER })

        expect(findSiteIcon).toHaveBeenCalledWith('acme.com')
        expect(iconWritten()).toBeUndefined()
    })

    it('keeps a logo picked by hand', async () => {
        workspaceWithIcon('https://db.rerun.test/storage/v1/object/public/workspace-logos/7/logo.webp')

        await ensureWorkspaceNamed({ workspaceId: WORKSPACE_ID, userId: FOUNDER })

        expect(iconWritten()).toBeUndefined()
    })
})
