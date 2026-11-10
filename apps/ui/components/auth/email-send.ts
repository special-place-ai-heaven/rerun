import { CaptchaError } from '@/components/auth/captcha/captcha-error'
import { detectInAppBrowser } from '@/lib/in-app-browser'
import { track } from '@rerun/analytics/client'

const MESSAGE_LIMIT = 200

// Supabase gives up on a request after ten seconds while the email it is sending often still goes
// out. The code step offers Resend, so moving on to it is safe and keeps a late code usable.
export function isSlowSend(error: unknown): boolean {
    const { status, code } = (typeof error === 'object' && error !== null ? error : {}) as { status?: unknown; code?: unknown }
    return status === 504 || code === 'request_timeout'
}
export const SLOW_SEND_MESSAGE = 'Sending took longer than usual. The code may still arrive: check your inbox and spam folder, or resend it.'

// A refusal from the server, with the reason analytics reports.
export class EmailSendError extends Error {
    constructor(
        message: string,
        readonly reason: string
    ) {
        super(message)
    }
}

function failure(error: unknown) {
    if (error instanceof CaptchaError) return error.analytics
    if (error instanceof EmailSendError) return { reason: error.reason }
    return { reason: 'client_error', message: (error instanceof Error ? error.message : String(error)).slice(0, MESSAGE_LIMIT) }
}

// Every "Send code" by email that sends nothing ends in `email_verification_failed`, whether the
// robot check turned the visitor away, the server refused, or the call itself broke.
export async function trackEmailSend<T>(send: () => Promise<T>): Promise<T> {
    try {
        return await send()
    } catch (error) {
        track('email_verification_failed', { ...failure(error), in_app_browser: detectInAppBrowser(navigator.userAgent) ?? undefined })
        throw error
    }
}
