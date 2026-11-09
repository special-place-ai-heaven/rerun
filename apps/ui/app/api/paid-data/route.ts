import { authenticateEngineToken } from '@/app/api/_services/workspace-engine.service'
import { BILLING_ENABLED } from '@rerun/cloud/billing'
import { paidDataPriceMultiplier } from '@/lib/paid-data/pricing'

// What the engine asks before it offers paid data. This install sells none, so the answer is always
// "off"; the route must still answer 200 with a price, or the engine reads the silence as "on"
// (apps/engine/src/paid-data/price.ts) and offers tools whose every call would fail.
export const dynamic = 'force-dynamic'

function bearerToken(req: Request): string {
    const header = req.headers.get('authorization') ?? ''
    return header.startsWith('Bearer ') ? header.slice(7) : ''
}

export async function GET(req: Request): Promise<Response> {
    const token = bearerToken(req)
    if (!token || !(await authenticateEngineToken(token))) return Response.json({ error: 'Unauthorized' }, { status: 401 })
    return Response.json({ enabled: BILLING_ENABLED, priceMultiplier: paidDataPriceMultiplier() })
}
