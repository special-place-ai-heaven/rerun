import 'server-only'
import { callerRateKey } from '@/lib/auth/caller-ip'
import { createServiceRoleClient } from '@/supabase/serviceRole'

// The public signup it stands in for allowed 30 per five minutes per address, for sign-ins as well.
// Only creations are counted here, and an office rarely opens ten accounts in the same hour.
export const MAX_SIGN_UPS_PER_IP = 10
const SIGN_UP_WINDOW_SECONDS = 60 * 60
// Every ask for a code counts too, not only the creations: the route is public and answers whether a
// code is on its way, so a loop over addresses runs out here first.
export const MAX_CODE_ASKS_PER_IP = 30
// Every auth email counts against its address too, whichever path asked for it: an attacker who talks
// to Supabase directly skips the captcha and the per-network pace, not the hook that mails the code.
export const MAX_AUTH_EMAILS_PER_ADDRESS = 10

// Counted under its own scope of the sign-up window. False once the caller asked too often.
export async function claimEmailCodeAsk(ip: string): Promise<boolean> {
    const { data, error } = await createServiceRoleClient().rpc('claim_email_sign_up', { p_ip: `code:${callerRateKey(ip)}`, p_ip_max: MAX_CODE_ASKS_PER_IP, p_window_seconds: SIGN_UP_WINDOW_SECONDS })
    return !error && data === true
}

// Counted per address. A counter that cannot be read lets the email through: an outage of the
// database must not lock every sign-in out.
export async function claimAuthEmailSend(email: string): Promise<boolean> {
    const { data, error } = await createServiceRoleClient().rpc('claim_email_sign_up', { p_ip: `mail:${email}`, p_ip_max: MAX_AUTH_EMAILS_PER_ADDRESS, p_window_seconds: SIGN_UP_WINDOW_SECONDS })
    if (error) {
        console.error('[email-sign-up] claim_email_sign_up (per address) failed', error.message)
        return true
    }
    return data === true
}

export type EmailAccountFailure = 'blocked_domain' | 'not_allowed' | 'too_many' | 'unavailable'

// Who may open an account: `SIGN_UP_EMAILS`, comma-separated addresses or `@domain` entries. Unset,
// anyone may. An account that exists signs in either way.
export function signUpAllowed(email: string): boolean {
    const entries = (process.env.SIGN_UP_EMAILS ?? '').split(',').map(entry => entry.trim().toLowerCase()).filter(Boolean)
    if (entries.length === 0) return true
    const address = email.toLowerCase()
    return entries.some(entry => (entry.startsWith('@') ? address.endsWith(entry) : entry === address))
}
// `created` is whether this call opened the account: the address is new, and the sign-in about to
// follow is a signup.
export type EmailAccountResult = { ok: true; created: boolean } | { ok: false; error: EmailAccountFailure }

const refused = (error: EmailAccountFailure) => ({ ok: false as const, error })

export type EmailLookupResult = { ok: true; exists: boolean } | { ok: false; error: EmailAccountFailure }

// An open invitation lets its address open an account even when SIGN_UP_EMAILS does not list it:
// whoever invited them already vouched for it. Invitations are stored lowercase.
async function hasPendingInvitation(admin: ReturnType<typeof createServiceRoleClient>, email: string): Promise<boolean> {
    const { data, error } = await admin.from('workspace_invitations').select('id').eq('email', email.toLowerCase()).eq('status', 'pending').gt('expires_at', new Date().toISOString()).limit(1)
    if (error) {
        console.error('[email-sign-up] workspace_invitations lookup failed', error.message)
        return false
    }
    return (data?.length ?? 0) > 0
}

// Whether the address has an account, and when it has none, whether one may open on its domain.
// The domain rule lives here as well as in `before_user_created`: that hook only sees a creation,
// never an anonymous visitor claiming the address on an account that already exists.
export async function lookupEmailForSignUp(email: string): Promise<EmailLookupResult> {
    const admin = createServiceRoleClient()
    const { data: exists, error: existsError } = await admin.rpc('check_email_exists', { email })
    if (existsError) {
        console.error('[email-sign-up] check_email_exists failed', existsError.message)
        return refused('unavailable')
    }
    if (exists) return { ok: true, exists: true }
    if (!signUpAllowed(email) && !(await hasPendingInvitation(admin, email))) return refused('not_allowed')

    const { data: blocked, error: blockedError } = await admin.rpc('email_domain_is_blocked', { p_email: email })
    if (blockedError) {
        console.error('[email-sign-up] email_domain_is_blocked failed', blockedError.message)
        return refused('unavailable')
    }
    if (blocked) return refused('blocked_domain')
    return { ok: true, exists: false }
}

// An address with no account gets one before its first code is asked for, so the code signs into
// it rather than creating it. Created by the admin API, the account never holds a password anyone
// knows: the public signup would let whoever files an address first set one on it. `email` is
// normalized already.
export async function ensureEmailAccount(email: string, ip: string): Promise<EmailAccountResult> {
    const lookup = await lookupEmailForSignUp(email)
    if (!lookup.ok) return lookup
    if (lookup.exists) return { ok: true, created: false }

    const admin = createServiceRoleClient()
    const { data: claimed, error: claimError } = await admin.rpc('claim_email_sign_up', { p_ip: callerRateKey(ip), p_ip_max: MAX_SIGN_UPS_PER_IP, p_window_seconds: SIGN_UP_WINDOW_SECONDS })
    if (claimError) {
        console.error('[email-sign-up] claim_email_sign_up failed', claimError.message)
        return refused('unavailable')
    }
    if (!claimed) return refused('too_many')

    // Created confirmed: with signups off in Supabase, a code for an unconfirmed account counts as a
    // signup and is refused. Only the code mailed next signs anyone in, so nothing is given away.
    const { error } = await admin.auth.admin.createUser({ email, email_confirm: true })
    // Another tab of the same visitor may have created it a moment earlier, and counts it there.
    if (error && error.code !== 'email_exists') {
        console.error('[email-sign-up] account creation failed', error.message)
        return refused('unavailable')
    }
    return { ok: true, created: !error }
}
