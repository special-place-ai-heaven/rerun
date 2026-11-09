import { DEFAULT_ADMIN_EMAILS } from '@rerun/cloud/admin'

// Who may use the admin affordances: `ADMIN_EMAILS` (or `NEXT_PUBLIC_ADMIN_EMAILS`, the one the
// browser bundle can read), comma-separated. Without either, the deployment's built-in list applies.
// `||`, not `??`: an image built without the browser list bakes it in as '', and the server must then
// read ADMIN_EMAILS from its own environment.
export function adminEmails(): string[] {
    const configured = process.env.NEXT_PUBLIC_ADMIN_EMAILS || process.env.ADMIN_EMAILS
    if (!configured) return DEFAULT_ADMIN_EMAILS
    return configured
        .split(',')
        .map(email => email.trim())
        .filter(Boolean)
}

export function isAdminEmail(email: string | null | undefined): boolean {
    if (!email) return false
    const normalized = email.toLowerCase()
    return adminEmails().some(admin => admin.toLowerCase() === normalized)
}
