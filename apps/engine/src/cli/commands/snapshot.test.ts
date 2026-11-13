import { mkdtempSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { resolve } from 'node:path'
import { vi } from 'vitest'

process.env.RERUN_DATA_DIR = mkdtempSync(resolve(tmpdir(), 'rerun-cli-snapshot-'))
process.env.RERUN_API_KEY = ''

const { afterEach, beforeEach, describe, expect, it } = await import('vitest')
const { mkdir, readdir, readFile, rm, writeFile } = await import('node:fs/promises')
const { createClient } = await import('@libsql/client')
const { agentDir, agentDataDir, configPath, dataDir, systemDbPath } = await import('../../config/paths.js')
const { snapshotCommand } = await import('./snapshot.js')

const backups = () => resolve(dataDir(), 'backups')
let out = ''

async function coworker(id: string, withDb: boolean) {
    await mkdir(agentDataDir(id), { recursive: true })
    await writeFile(configPath(id), '{}')
    if (!withDb) return
    const client = createClient({ url: `file:${systemDbPath(id)}` })
    await client.execute('CREATE TABLE t (a TEXT)')
    await client.execute({ sql: 'INSERT INTO t VALUES (?)', args: [id] })
    client.close()
}

beforeEach(async () => {
    out = ''
    process.exitCode = undefined
    await rm(resolve(dataDir(), 'agents'), { recursive: true, force: true })
    await rm(backups(), { recursive: true, force: true })
    vi.spyOn(process.stdout, 'write').mockImplementation(chunk => {
        out += String(chunk)
        return true
    })
})

afterEach(() => {
    vi.restoreAllMocks()
    process.exitCode = undefined
})

describe('rerun snapshot', () => {
    it('copies every system database, checks each copy and leaves the sources untouched', async () => {
        await coworker('a1', true)
        await coworker('a2', true)
        await coworker('a3', false)
        const before = [await readFile(systemDbPath('a1')), await readFile(systemDbPath('a2'))]
        await snapshotCommand([])
        const report = JSON.parse(out.trim())
        expect(report).toMatchObject({ copies: 2, ok: 2 })
        expect(report.bytes).toBeGreaterThan(0)
        expect(process.exitCode).toBeUndefined()
        const folders = await readdir(backups())
        expect(folders).toHaveLength(1)
        expect((await readdir(resolve(backups(), folders[0]!))).sort()).toEqual(['a1.system.db', 'a2.system.db'])
        expect(await readFile(systemDbPath('a1'))).toEqual(before[0])
        expect(await readFile(systemDbPath('a2'))).toEqual(before[1])
    })

    it('keeps the newest N snapshot folders and ignores other names', async () => {
        await coworker('a1', true)
        for (const n of ['20260101T000000Z', '20260102T000000Z', '20260103T000000Z', 'notes']) {
            await mkdir(resolve(backups(), n), { recursive: true })
        }
        await snapshotCommand(['--keep', '2'])
        const left = (await readdir(backups())).sort()
        expect(left).toHaveLength(3)
        expect(left).toContain('notes')
        expect(left).not.toContain('20260101T000000Z')
        expect(left).not.toContain('20260102T000000Z')
        expect(left).toContain('20260103T000000Z')
    })

    it('fails and removes nothing when a source cannot be copied', async () => {
        await coworker('a1', true)
        await coworker('a2', false)
        await writeFile(systemDbPath('a2'), 'this is not a database'.repeat(50))
        await mkdir(resolve(backups(), '20260101T000000Z'), { recursive: true })
        await mkdir(resolve(backups(), '20260102T000000Z'), { recursive: true })
        await snapshotCommand(['--keep', '1'])
        expect(process.exitCode).toBe(1)
        const left = await readdir(backups())
        expect(left).toContain('20260101T000000Z')
        expect(left).toContain('20260102T000000Z')
        expect(agentDir('a2')).toBeTruthy()
    })
})
