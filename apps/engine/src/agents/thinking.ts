import type { Provider, AgentConfig } from '@rerun/contracts'
import type { streamText } from 'ai'
import { REASONING_REQUEST } from './openrouter-reasoning.js'
import { reasoningProviderOptions } from './reasoning.js'

type ProviderOptions = NonNullable<Parameters<typeof streamText>[0]['providerOptions']>
export type ThinkingLevel = NonNullable<AgentConfig['thinkingLevel']>

export type ThinkingSettings = {
    /** `thinking` setting of the `claude` CLI provider. */
    claudeThinking?: { type: 'adaptive'; display: 'summarized'; effort?: ThinkingLevel }
    /** AI SDK `providerOptions` for anthropic, openai and google. */
    providerOptions?: ProviderOptions
    /** `reasoning` object added to the OpenRouter request body (`rerun`, `openrouter`). */
    openrouterReasoning?: { enabled: boolean; effort?: ThinkingLevel }
}

/** What the Claude CLI provider is given today (providers.ts builds the same literal inline). */
export const CLAUDE_DEFAULT_THINKING = { type: 'adaptive', display: 'summarized' } as const

/**
 * The settings that carry a thinking level to one provider. No level gives exactly what each provider
 * sends today. Providers with no probed option (codex, opencode, custom) get the no-level result
 * whatever the level.
 */
export function thinkingSettingsFor(provider: Provider, model: string, level: ThinkingLevel | null | undefined): ThinkingSettings {
    const base = (): ThinkingSettings => {
        if (provider === 'claude') return { claudeThinking: CLAUDE_DEFAULT_THINKING }
        if (provider === 'rerun' || provider === 'openrouter') return { openrouterReasoning: REASONING_REQUEST }
        return { providerOptions: reasoningProviderOptions(provider, model) }
    }
    if (!level) return base()
    switch (provider) {
        case 'claude':
            return { claudeThinking: { ...CLAUDE_DEFAULT_THINKING, effort: level } }
        case 'anthropic':
            return { providerOptions: { anthropic: { thinking: CLAUDE_DEFAULT_THINKING, effort: level } } }
        case 'openai':
            return { providerOptions: { openai: { reasoningSummary: 'auto', reasoningEffort: level } } }
        case 'google':
            return { providerOptions: { google: { thinkingConfig: { includeThoughts: true, thinkingLevel: level } } } }
        case 'rerun':
        case 'openrouter':
            return { openrouterReasoning: { ...REASONING_REQUEST, effort: level } }
        default:
            return base()
    }
}
