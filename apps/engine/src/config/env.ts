import { z } from 'zod'
import { homedir } from 'node:os'
import { resolve } from 'node:path'
import { closeSync, readFileSync } from 'node:fs'

const schema = z.object({
    RERUN_DATA_DIR: z.string().default(resolve(homedir(), '.rerun')),
    RERUN_PORT: z.coerce.number().int().positive().default(3000),
    RERUN_HOST: z.string().default('0.0.0.0'),
    RERUN_API_KEY: z.string().optional(),
    RERUN_HUB_BASE_URL: z.preprocess(v => (v === '' ? undefined : v), z.string().url().optional()),
    RERUN_LOG_LEVEL: z.enum(['fatal', 'error', 'warn', 'info', 'debug', 'trace']).default('info'),
    // Absolute path to the Codex CLI. Set it when the binary is not on the service user's PATH,
    // or to keep the provider's bundled @openai/codex in node_modules/.bin from shadowing it.
    RERUN_CODEX_PATH: z.string().optional(),
    // `on` opens the desktop of the agents on this box ahead of the release, `off` keeps it shut after.
    RERUN_DESKTOP: z.string().optional(),
})

export type Env = z.infer<typeof schema>

let cached: Env | null = null

// The engine key lives here and nowhere else: not in process.env, and not in a child's environment.
// The image launcher delivers it on an inherited descriptor named by RERUN_KEY_FD; a start without
// a launcher (systemd, a checkout) still has it in RERUN_API_KEY, which env() falls back to.
let heldKey: string | undefined

// Read the descriptor once and close it. Called first thing in the engine entry, before any module
// that may call env().
export function takeKeyFromDescriptor(): void {
    const signalled = process.env.RERUN_KEY_FD
    if (signalled === undefined) return
    delete process.env.RERUN_KEY_FD
    const fd = Number(signalled)
    let key = ''
    try {
        if (Number.isInteger(fd) && fd > 2) key = readFileSync(fd, 'utf8').trim()
    } catch {
        key = ''
    } finally {
        if (Number.isInteger(fd) && fd > 2) {
            try {
                closeSync(fd)
            } catch {
                // already closed
            }
        }
    }
    if (!key) throw new Error('the launcher signalled a key descriptor, but it held no key')
    heldKey = key
    if (cached) cached = { ...cached, RERUN_API_KEY: key }
}

export function env(): Env {
    if (cached) return cached
    if (process.env.RERUN_KEY_FD !== undefined && heldKey === undefined) throw new Error('the key descriptor was signalled but not read: call takeKeyFromDescriptor() first')
    const parsed = schema.safeParse(process.env)
    if (!parsed.success) {
        const issues = parsed.error.issues.map(i => `${i.path.join('.')}: ${i.message}`).join(', ')
        throw new Error(`Invalid environment: ${issues}`)
    }
    cached = heldKey === undefined ? parsed.data : { ...parsed.data, RERUN_API_KEY: heldKey }
    return cached
}

// The key and the hub of a server that paired itself are only known once the data-dir is read,
// after the first modules have read the environment: they are set here. The key goes to the holder
// only, the hub also to process.env.
export function setEnv(values: Partial<Pick<Env, 'RERUN_API_KEY' | 'RERUN_HUB_BASE_URL'>>): void {
    if (values.RERUN_API_KEY !== undefined) heldKey = values.RERUN_API_KEY
    if (values.RERUN_HUB_BASE_URL !== undefined) process.env.RERUN_HUB_BASE_URL = values.RERUN_HUB_BASE_URL
    if (cached) cached = { ...cached, ...values }
}

// Until the desktop is released a box has no screen, no computer tools and installs none of its
// packages. Flipping this opens it on every box at its next update.
const DESKTOP_RELEASED = true

export function desktopEnabled(): boolean {
    const flag = env().RERUN_DESKTOP
    return flag === 'on' || (DESKTOP_RELEASED && flag !== 'off')
}
