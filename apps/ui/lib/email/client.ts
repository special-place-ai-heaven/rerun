// Deliberately no 'server-only' import: this module is pulled in both by email.service.ts (Next
// server) and by the Trigger.dev tasks that send scheduled expert invites, which are bundled
// outside the Next.js RSC pipeline and would crash on the server-only marker.
import nodemailer from 'nodemailer'
import { Resend } from 'resend'

import { DEFAULT_SENDERS } from '@rerun/cloud/senders'
import { APP_URL } from '@/lib/app-url'

export { APP_URL, notificationUrl } from '@/lib/app-url'

// The fallback has to be an address on a Resend-verified sending domain: a root domain without SPF
// nor a DKIM key 403s, and would land unauthenticated if it ever went out.
export const TRANSACTIONAL_FROM = process.env.RESEND_FROM || process.env.SMTP_FROM || DEFAULT_SENDERS.transactional
// Expert invites ship from their own verified domain so cold outreach never touches the
// reputation of the transactional sender.
export const EXPERTS_FROM = process.env.RESEND_EXPERTS_FROM || process.env.SMTP_FROM || DEFAULT_SENDERS.experts
// Re-engagement mail gets its own domain too. Nobody asked for a nudge, so it is where the
// complaints and the unsubscribes come from, and a complaint must never land on the domain that
// carries sign-in links, run failures and billing.
export const MARKETING_FROM = process.env.RESEND_MARKETING_FROM || process.env.SMTP_FROM || DEFAULT_SENDERS.marketing
// The newsletter has a domain of its own so a bulk editorial send answers for itself, but an
// unconfigured environment falls back to the marketing sender rather than the transactional one: a
// blast is never worth putting sign-in delivery at stake.
export const NEWSLETTER_FROM = process.env.RESEND_NEWSLETTER_FROM ?? MARKETING_FROM
// Every sending subdomain has receiving disabled, so a reply to the `from` address bounces.
// Pointing it at a mailbox that exists is both what makes the emails answerable and one of the
// strongest positive signals a mailbox provider has: people reply to senders they trust.
export const REPLY_TO = process.env.RESEND_REPLY_TO ?? DEFAULT_SENDERS.replyTo

export type SendEmailResult = { ok: true; id: string | null; skipped?: boolean } | { ok: false; error: string }

// Staging runs on a clone of the production database, so every recipient is a real user. When
// EMAIL_REDIRECT_TO is set, the whole delivery is rerouted to that single inbox and the intended
// recipient is moved into the subject, which keeps the emails testable without ever reaching anyone.
export function redirectDelivery(to: string, subject: string): { to: string; subject: string } {
    const inbox = process.env.EMAIL_REDIRECT_TO
    if (!inbox) return { to, subject }
    return { to: inbox, subject: `[staging → ${to}] ${subject}` }
}

// Production and staging both run with NODE_ENV=production, so nothing in the runtime tells them
// apart. EMAIL_REDIRECT_TO does: it is set everywhere the
// recipients are a clone of the real users, and left unset only where they are the real users.
export const IS_PRODUCTION_MAILER = process.env.NODE_ENV === 'production' && !process.env.EMAIL_REDIRECT_TO

type SendPayload = Parameters<Resend['emails']['send']>[0]
type SendResponse = Awaited<ReturnType<Resend['emails']['send']>>
// The one call every sender here makes. Resend answers it, or the install's own mailbox does.
export type Mailer = { emails: { send(payload: SendPayload): Promise<SendResponse> } }

let client: Mailer | null = null

// SMTP_HOST (with SMTP_PORT, SMTP_USER, SMTP_PASS) sends through a mailbox the install already has;
// otherwise RESEND_API_KEY sends through Resend. Neither: no client, and nothing is sent.
export function getResendClient(): Mailer | null {
    if (process.env.SMTP_HOST) return (client ??= smtpMailer())
    const key = process.env.RESEND_API_KEY
    if (!key) return null
    if (!client) client = new Resend(key)
    return client
}

function smtpMailer(): Mailer {
    const port = Number(process.env.SMTP_PORT || 465)
    const transport = nodemailer.createTransport({
        host: process.env.SMTP_HOST,
        port,
        secure: port === 465,
        auth: process.env.SMTP_USER ? { user: process.env.SMTP_USER, pass: process.env.SMTP_PASS } : undefined,
    })
    return {
        emails: {
            async send(payload) {
                const { from, to, cc, bcc, replyTo, subject, html, text, headers } = payload as Extract<SendPayload, { html: string }>
                try {
                    const info = await transport.sendMail({ from, to, cc, bcc, replyTo, subject, html, text, headers })
                    return { data: { id: info.messageId }, error: null } as SendResponse
                } catch (err) {
                    // Not a rate limit, so the throttle never sends it again: the server may have taken it.
                    return { data: null, error: { name: 'application_error', message: err instanceof Error ? err.message : String(err) } } as SendResponse
                }
            },
        },
    }
}
