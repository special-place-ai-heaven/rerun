import { beforeEach, describe, expect, it, vi } from 'vitest'

const fetchPublic = vi.hoisted(() => vi.fn())
const fetchLogoBytes = vi.hoisted(() => vi.fn())
vi.mock('@/lib/net/public-fetch', () => ({ fetchPublic }))
vi.mock('@/lib/workspace/fetch-logo', () => ({ fetchLogoBytes, rasterizeVectorLogo: async () => new Uint8Array([0x89, 0x50, 0x4e, 0x47, 1]) }))

const { findSiteIcon, imageType, parseIconLinks, resetSiteIconsForTests } = await import('./site-icon.server')

const PNG = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a])
const ICO = new Uint8Array([0x00, 0x00, 0x01, 0x00, 0x01])
const SVG = new TextEncoder().encode('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>')

function homePage(html: string): Response {
    return new Response(html, { status: 200, headers: { 'content-type': 'text/html; charset=utf-8' } })
}

beforeEach(() => {
    resetSiteIconsForTests()
    fetchPublic.mockReset()
    fetchLogoBytes.mockReset()
})

describe('parseIconLinks', () => {
    it('ranks the declared icons biggest first and resolves them on the page', () => {
        const html = `<head>
            <link rel="icon" href="/favicon-16.png">
            <link rel='icon' sizes="32x32 64x64" href='/favicon-64.png'>
            <link href=/touch.png rel="apple-touch-icon">
            <link rel="stylesheet" href="/site.css">
            <link rel="shortcut icon" type="image/svg+xml" href="https://cdn.acme.com/mark.svg">
        </head>`
        expect(parseIconLinks(html, 'https://acme.com/')).toEqual(['https://cdn.acme.com/mark.svg', 'https://acme.com/touch.png', 'https://acme.com/favicon-64.png', 'https://acme.com/favicon-16.png'])
    })
})

describe('imageType', () => {
    it('reads the type off the bytes, not off a header the site may get wrong', () => {
        expect(imageType(PNG)).toBe('image/png')
        expect(imageType(ICO)).toBe('image/x-icon')
        expect(imageType(SVG)).toBe('image/svg+xml')
        expect(imageType(new TextEncoder().encode('<html>not an icon</html>'))).toBeNull()
    })
})

describe('findSiteIcon', () => {
    it('takes the first declared icon the site serves', async () => {
        fetchPublic.mockResolvedValue(homePage('<link rel="apple-touch-icon" href="/touch.png">'))
        fetchLogoBytes.mockResolvedValue({ ok: true, bytes: PNG })

        expect(await findSiteIcon('acme.com')).toEqual({ bytes: PNG, contentType: 'image/png' })
        expect(fetchLogoBytes).toHaveBeenCalledTimes(1)
        expect(fetchLogoBytes).toHaveBeenCalledWith('https://acme.com/touch.png')
    })

    it('falls back on the paths every browser tries when the page declares nothing', async () => {
        fetchPublic.mockResolvedValue(homePage('<title>Acme</title>'))
        fetchLogoBytes.mockResolvedValueOnce({ ok: false, error: 'none' }).mockResolvedValueOnce({ ok: true, bytes: ICO })

        expect(await findSiteIcon('acme.com')).toEqual({ bytes: ICO, contentType: 'image/x-icon' })
        expect(fetchLogoBytes.mock.calls.map(call => call[0])).toEqual(['https://acme.com/apple-touch-icon.png', 'https://acme.com/favicon.ico'])
    })

    it('draws a vector to PNG before this origin serves it', async () => {
        fetchPublic.mockResolvedValue(homePage('<link rel="icon" href="/mark.svg">'))
        fetchLogoBytes.mockResolvedValue({ ok: true, bytes: SVG })

        expect((await findSiteIcon('acme.com'))?.contentType).toBe('image/png')
    })

    it('answers none for a site with no icon, and asks only once a day', async () => {
        fetchPublic.mockRejectedValue(new Error('acme.example is not a public host'))
        fetchLogoBytes.mockResolvedValue({ ok: false, error: 'none' })

        expect(await findSiteIcon('acme.example')).toBeNull()
        expect(await findSiteIcon('acme.example')).toBeNull()
        expect(fetchPublic).toHaveBeenCalledTimes(1)
    })
})
