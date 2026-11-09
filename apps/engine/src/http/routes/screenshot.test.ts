import { describe, expect, it, vi } from 'vitest'
import { setEnv } from '../../config/env.js'
import { createScreenshotRoutes, type Shooter } from './screenshot.js'

const HUB = 'http://app:3000'
const PNG = Buffer.from([0x89, 0x50, 0x4e, 0x47])

function routes(shoot: Shooter) {
    setEnv({ RERUN_HUB_BASE_URL: HUB })
    return createScreenshotRoutes(shoot)
}

const query = (params: Record<string, string>) => `/?${new URLSearchParams(params)}`

describe('GET /screenshot', () => {
    it('shoots a page of the hub with the size, scale, wait and theme asked for', async () => {
        const shoot = vi.fn<Shooter>().mockResolvedValue(PNG)
        const res = await routes(shoot).request(query({ url: `${HUB}/og/board/1?t=x`, width: '1200', height: '630', scale: '2', format: 'png', wait_for: '[data-og-ready="true"]', timeout: '30000', dark: '1' }))

        expect(res.status).toBe(200)
        expect(res.headers.get('content-type')).toBe('image/png')
        expect(Buffer.from(await res.arrayBuffer())).toEqual(PNG)
        expect(shoot).toHaveBeenCalledWith({ url: `${HUB}/og/board/1?t=x`, width: 1200, height: 630, scale: 2, format: 'png', waitFor: '[data-og-ready="true"]', timeoutMs: 30000, dark: true })
    })

    it('answers WebP when asked, and leaves the theme to the page when none is given', async () => {
        const shoot = vi.fn<Shooter>().mockResolvedValue(PNG)
        const res = await routes(shoot).request(query({ url: `${HUB}/p/page`, width: '800', height: '600', format: 'webp' }))

        expect(res.headers.get('content-type')).toBe('image/webp')
        expect(shoot).toHaveBeenCalledWith(expect.objectContaining({ format: 'webp', scale: 1, waitFor: null, dark: null }))
    })

    it('refuses a page outside the hub before any browser opens', async () => {
        const shoot = vi.fn<Shooter>()
        const res = await routes(shoot).request(query({ url: 'http://169.254.169.254/latest/meta-data', width: '800', height: '600' }))

        expect(res.status).toBe(403)
        expect(shoot).not.toHaveBeenCalled()
    })
})
