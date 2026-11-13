import { mkdirSync, mkdtempSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { vi } from 'vitest'

process.env.RERUN_DATA_DIR = mkdtempSync(resolve(tmpdir(), 'rerun-skim-'))

const { beforeAll, describe, expect, it } = await import('vitest')
const { skimPagesTools } = await import('./skim-pages.js')
const { createScreenshotStore } = await import('../../runtime/screenshots.js')
const { workspaceDir } = await import('../../config/paths.js')

const root = workspaceDir('skim-agent')
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47])

function setup() {
    const screenshots = createScreenshotStore()
    const ctx = { agent: { id: 'skim-agent' }, screenshots } as any
    const run = (input: Record<string, unknown>) => (skimPagesTools(ctx).skim_pages as any).execute(input, { toolCallId: 'c', messages: [] })
    return { screenshots, run }
}

beforeAll(() => {
    mkdirSync(resolve(root, 'keys'), { recursive: true })
    mkdirSync(resolve(root, 'dir/.git'), { recursive: true })
    mkdirSync(resolve(root, 'dir/node_modules'), { recursive: true })
    const long = Array.from({ length: 400 }, (_, i) => `line ${i} job started id=a1b2c3d4e5f6 count 98765 ok`).join('\n')
    writeFileSync(resolve(root, 'long.log'), long)
    writeFileSync(resolve(root, 'short.txt'), 'hello a1b2c3d4e5f6 and 98765 and 12')
    for (const f of ['.env', 'keys/id_rsa', 'secret.txt', 'token-list.txt', 'a.pem']) writeFileSync(resolve(root, f), 'x=1')
    writeFileSync(resolve(root, 'dir/a.txt'), 'alpha text')
    writeFileSync(resolve(root, 'dir/.git/config'), 'gitsecretcontent')
    writeFileSync(resolve(root, 'dir/node_modules/m.js'), 'nodemodcontent')
    writeFileSync(resolve(root, 'dir/bin.dat'), Buffer.from([0, 1, 2, 0, 3]))
})

describe('skim_pages', () => {
    it('renders a long file as pages, one per call, as PNG', async () => {
        const { screenshots, run } = setup()
        const first = await run({ path: 'long.log' })
        expect(first.pages).toBeGreaterThanOrEqual(3)
        expect(first.page).toBe(1)
        expect(screenshots.get(first.screenshotId)!.image.subarray(0, 4)).toEqual(PNG)
        expect(screenshots.get(first.screenshotId)!.mediaType).toBe('image/png')
        const second = await run({ path: 'long.log', page: 2 })
        expect(second.page).toBe(2)
        expect(second.screenshotId).not.toBe(first.screenshotId)
        expect(screenshots.get(second.screenshotId)!.image.equals(screenshots.get(first.screenshotId)!.image)).toBe(false)
        expect(first.note).toContain('Read the file for any exact value')
    })

    it('refuses a page past the end', async () => {
        const { screenshots, run } = setup()
        const { pages } = await run({ path: 'long.log' })
        await expect(run({ path: 'long.log', page: pages + 1 })).rejects.toThrow(/page/)
        await expect(run({ path: 'long.log', page: 0 })).rejects.toThrow(/page/)
        expect(screenshots.get('none')).toBeUndefined()
    })

    it('takes ids and numbers from the text', async () => {
        const { run } = setup()
        const r = await run({ path: 'short.txt' })
        expect(r.pages).toBe(1)
        expect(r.exact.ids).toEqual(['a1b2c3d4e5f6'])
        expect(r.exact.numbers).toEqual(['98765'])
    })

    it.each(['.env', 'keys/id_rsa', '../outside', 'secret.txt', 'token-list.txt', 'a.pem'])('refuses %s and stores nothing', async path => {
        const { screenshots, run } = setup()
        const spy = vi.spyOn(screenshots, 'add')
        await expect(run({ path })).rejects.toThrow()
        expect(spy).not.toHaveBeenCalled()
    })

    it('lists a folder tree first and skips .git and node_modules', async () => {
        const { run, screenshots } = setup()
        const spy = vi.spyOn(screenshots, 'add')
        const r = await run({ path: 'dir' })
        expect(r.tree).toContain('a.txt')
        expect(r.tree).not.toContain('.git/config')
        expect(r.tree).not.toContain('m.js')
        expect(r.exact.ids).toEqual([])
        expect(spy).toHaveBeenCalledOnce()
    })
})
