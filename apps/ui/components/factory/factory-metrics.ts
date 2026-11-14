// What the factory bar shows. The run measures are Rerun's own (statsMetricSchema in
// @rerun/contracts, the same the stats pages chart); the job counts come from the delegator's
// ledger; plan and sign-in from the Claude connection. Each carries its definition for the hover.

export type MetricKey =
    | 'queued' | 'building' | 'review' | 'checks' | 'shipped'
    | 'runs' | 'totalTokens' | 'cachedShare' | 'avgDuration' | 'errorRate'
    | 'planWeek' | 'signIn'

export type MetricGroup = 'jobs' | 'runs' | 'plan'

export type MetricDef = { key: MetricKey; group: MetricGroup; label: string; definition: string; source: string }

export const METRICS: MetricDef[] = [
    { key: 'queued', group: 'jobs', label: 'Queued', definition: 'Issues the delegator has taken and not yet sent to a builder.', source: 'ledger: jobs waiting or queued' },
    { key: 'building', group: 'jobs', label: 'Building', definition: 'Builds and fixes running now, every copy counted.', source: 'ledger: jobs building or fixing' },
    { key: 'review', group: 'jobs', label: 'Review', definition: 'Reviews running now.', source: 'ledger: jobs reviewing' },
    { key: 'checks', group: 'jobs', label: 'Checks', definition: 'Approved pull requests waiting for their workflow runs.', source: 'ledger: jobs in checks' },
    { key: 'shipped', group: 'jobs', label: 'Shipped', definition: 'Pull requests merged into dev today.', source: 'ledger: merges since 00:00 UTC' },
    { key: 'runs', group: 'runs', label: 'Runs', definition: 'Runs of the factory coworkers in the last 24 hours.', source: 'stats: runs, count, 24h' },
    { key: 'totalTokens', group: 'runs', label: 'Tokens', definition: 'Total tokens of those runs.', source: 'stats: runs, totalTokens, 24h' },
    { key: 'cachedShare', group: 'runs', label: 'Cached', definition: 'Share of input tokens read from the cache.', source: 'stats: cachedInputTokens / inputTokens, 24h' },
    { key: 'avgDuration', group: 'runs', label: 'Avg run', definition: 'Average duration of a run.', source: 'stats: runs, avgDurationMs, 24h' },
    { key: 'errorRate', group: 'runs', label: 'Errors', definition: 'Share of runs that ended in error.', source: 'stats: runs, errorRate, 24h' },
    { key: 'planWeek', group: 'plan', label: 'Plan week', definition: 'Share of the Claude plan weekly window used.', source: 'connection plan limits (PlanLimitsBlock)' },
    { key: 'signIn', group: 'plan', label: 'Sign-in', definition: 'Minutes until the Claude sign-in expires; near the end the delegator holds sending.', source: 'connection sign-in expiry' },
]

export type MetricValues = Record<MetricKey, { text: string; fill?: number; warn?: boolean }>
