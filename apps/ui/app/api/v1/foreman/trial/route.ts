import { apiRoute } from '@/app/api/v1/_lib/api-route'
import type { ForemanTrialResult } from '@rerun/contracts'

export const dynamic = 'force-dynamic'

// The "Build my team" button of the app. This install sells no plan, so there is no trial to start:
// every workspace is already on, and the build itself is the next turn of the onboarding conversation.
export const POST = apiRoute({ auth: 'admin' }, async (): Promise<ForemanTrialResult> => ({ entitled: true }))
