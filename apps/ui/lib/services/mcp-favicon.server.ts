import { faviconUrl } from '@/lib/onboarding/site-favicon'
import { findSiteIcon } from '@/lib/onboarding/site-icon.server'

const TTL_MS = 24 * 60 * 60 * 1000

const checked = new Map<string, { url: string | null; at: number }>()

// The favicon service answers 404 for a domain it has never seen. Asking first means a row gets
// the plug icon instead of a broken image, which <Icon> has no fallback for.
export async function verifiedFaviconUrl(domain: string): Promise<string | null> {
    const cached = checked.get(domain)
    if (cached && Date.now() - cached.at < TTL_MS) return cached.url
    const url = faviconUrl(domain)
    const found = (await findSiteIcon(domain)) !== null
    checked.set(domain, { url: found ? url : null, at: Date.now() })
    return found ? url : null
}
