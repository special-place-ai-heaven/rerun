// The website step shows the site's favicon the moment what was typed reads as a real address. It
// is the only feedback that step can give before the analysis runs: the mark appearing says "we
// found you", and a typo says it by staying blank.
//
// Client side, so nothing here can reach for the brand-icon pipeline (lib/services/brand-icon.ts is
// server only, and its Simple Icons / logo.dev / FAL round trip costs seconds we do not have while
// someone is still typing). The app's own /api/favicon answers in one cached request instead, read
// from the site itself, and answers 404 for a site with no icon, which is what lets a typo show
// nothing rather than a globe.

import { APP_URL } from '@/lib/app-url'

const FAVICON_SERVICE = `${APP_URL}/api/favicon`

// A hostname worth asking a favicon for: labels, then a letters-only TLD of at least two. This is
// deliberately stricter than the browser's own parser, which happily accepts "acme" or "localhost".
const HOSTNAME = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/

// "https://www.acme.com/pricing", "www.acme.com" and "acme.com" all read as "acme.com". Anything
// that is not yet an address ("acme", "acme.c", an empty field) reads as null.
export function siteDomain(input: string): string | null {
    const trimmed = input.trim()
    if (!trimmed || /\s/.test(trimmed)) return null
    let host: string
    try {
        host = new URL(/^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`).hostname
    } catch {
        return null
    }
    host = host.toLowerCase().replace(/\.$/, '').replace(/^www\./, '')
    return HOSTNAME.test(host) ? host : null
}

// 128px for a 48px tile: the service downscales cleanly, and the smaller sizes it serves are the
// blurry 16px ico a browser tab uses.
export function faviconUrl(domain: string): string {
    return `${FAVICON_SERVICE}?sz=128&domain=${encodeURIComponent(domain)}`
}
