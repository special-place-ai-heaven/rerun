const TIMEOUT_MS = 10_000
// The most results Brave returns in one request, billed the same as a single result.
export const BRAVE_MAX_COUNT = 20

export type WebSearchResult = { title: string; url: string; snippet: string }

// `status` is null when Brave could not be reached at all.
export type BraveSearch = { status: number | null; ok: boolean; results: WebSearchResult[] }

type BraveResponse = { web?: { results?: { title?: string; url?: string; description?: string }[] } }

// Returns null when no key is configured: the caller has nothing to search with.
export async function searchBrave(query: string, count: number): Promise<BraveSearch | null> {
    const apiKey = process.env.BRAVE_SEARCH_API_KEY
    if (!apiKey) return null

    try {
        // Read at call time like the key; a self-hosted stand-in answers the same request elsewhere.
        const searchUrl = process.env.RERUN_BRAVE_SEARCH_URL ?? 'https://api.search.brave.com/res/v1/web/search'
        const res = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}&count=${count}`, {
            headers: { Accept: 'application/json', 'X-Subscription-Token': apiKey },
            signal: AbortSignal.timeout(TIMEOUT_MS),
        })
        if (!res.ok) return { status: res.status, ok: false, results: [] }

        const data = (await res.json()) as BraveResponse
        const results = (data.web?.results ?? []).filter(r => r.url).map(r => ({ title: r.title ?? '', url: r.url ?? '', snippet: r.description ?? '' }))
        return { status: res.status, ok: true, results }
    } catch {
        return { status: null, ok: false, results: [] }
    }
}
