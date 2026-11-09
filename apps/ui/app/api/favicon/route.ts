import { siteDomain } from '@/lib/onboarding/site-favicon'
import { findSiteIcon } from '@/lib/onboarding/site-icon.server'

// GET /api/favicon?domain=acme.com: the site's own icon, what `faviconUrl` points every <img> at.
// 404 when the site has none. Never a page: the response may not run or load anything.
export async function GET(request: Request): Promise<Response> {
    const domain = siteDomain(new URL(request.url).searchParams.get('domain') ?? '')
    const icon = domain ? await findSiteIcon(domain) : null
    const headers = { 'Content-Security-Policy': "default-src 'none'; sandbox", 'X-Content-Type-Options': 'nosniff' }
    if (!icon) return new Response(null, { status: 404, headers: { ...headers, 'Cache-Control': 'public, max-age=3600' } })
    return new Response(new Uint8Array(icon.bytes), { headers: { ...headers, 'Content-Type': icon.contentType, 'Cache-Control': 'public, max-age=86400' } })
}

export const HEAD = GET
