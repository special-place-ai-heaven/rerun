import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { searchBrave } from './brave'

const originalKey = process.env.BRAVE_SEARCH_API_KEY
const originalFetch = globalThis.fetch

function mockFetch(impl: (url: string, init?: RequestInit) => Promise<Response> | Response) {
    const fn = vi.fn(async (url: string, init?: RequestInit) => impl(url, init))
    globalThis.fetch = fn as unknown as typeof fetch
    return fn
}

describe('searchBrave', () => {
    beforeEach(() => {
        process.env.BRAVE_SEARCH_API_KEY = 'brave-key'
    })

    afterEach(() => {
        globalThis.fetch = originalFetch
        if (originalKey === undefined) delete process.env.BRAVE_SEARCH_API_KEY
        else process.env.BRAVE_SEARCH_API_KEY = originalKey
    })

    it('returns null without a key, and calls nothing', async () => {
        delete process.env.BRAVE_SEARCH_API_KEY
        const fetchMock = mockFetch(() => Response.json({}))

        await expect(searchBrave('rerun', 5)).resolves.toBeNull()
        expect(fetchMock).not.toHaveBeenCalled()
    })

    it('maps the results and sends the key in the subscription header', async () => {
        const fetchMock = mockFetch(() =>
            Response.json({
                web: {
                    results: [
                        { title: 'One', url: 'https://one.test', description: 'first' },
                        { title: 'Two', url: 'https://two.test' },
                    ],
                },
            }),
        )

        await expect(searchBrave('a & b', 2)).resolves.toEqual({
            status: 200,
            ok: true,
            results: [
                { title: 'One', url: 'https://one.test', snippet: 'first' },
                { title: 'Two', url: 'https://two.test', snippet: '' },
            ],
        })
        const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
        expect(url).toBe('https://api.search.brave.com/res/v1/web/search?q=a%20%26%20b&count=2')
        expect((init.headers as Record<string, string>)['X-Subscription-Token']).toBe('brave-key')
    })

    it('sends the request to RERUN_BRAVE_SEARCH_URL when it is set', async () => {
        process.env.RERUN_BRAVE_SEARCH_URL = 'http://webgate:8080/res/v1/web/search'
        const fetchMock = mockFetch(() => Response.json({ web: { results: [] } }))

        try {
            await searchBrave('rerun', 3)
        } finally {
            delete process.env.RERUN_BRAVE_SEARCH_URL
        }
        expect(fetchMock.mock.calls[0][0]).toBe('http://webgate:8080/res/v1/web/search?q=rerun&count=3')
    })

    it('answers an empty list when Brave found nothing', async () => {
        mockFetch(() => Response.json({ web: {} }))

        await expect(searchBrave('nothing', 5)).resolves.toEqual({ status: 200, ok: true, results: [] })
    })

    it('reports the status Brave refused with', async () => {
        mockFetch(() => new Response('rate limited', { status: 429 }))

        await expect(searchBrave('rerun', 5)).resolves.toEqual({ status: 429, ok: false, results: [] })
    })

    it('reports no status when Brave cannot be reached', async () => {
        mockFetch(() => {
            throw new Error('ECONNRESET')
        })

        await expect(searchBrave('rerun', 5)).resolves.toEqual({ status: null, ok: false, results: [] })
    })
})
