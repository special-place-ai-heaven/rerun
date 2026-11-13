import { describe, expect, it } from 'vitest'
import type { Provider } from '@rerun/contracts'
import { REASONING_REQUEST } from './openrouter-reasoning.js'
import { REASONING_OPTIONS } from './reasoning.js'
import { CLAUDE_DEFAULT_THINKING, thinkingSettingsFor } from './thinking.js'

const ALL: Provider[] = ['rerun', 'anthropic', 'claude', 'codex', 'openai', 'google', 'openrouter', 'opencode', 'custom']
const LEVELS = ['low', 'medium', 'high'] as const

describe('thinkingSettingsFor', () => {
    it.each(ALL)('null and undefined give today\'s constants for %s', (provider) => {
        const expected = {
            claudeThinking: provider === 'claude' ? CLAUDE_DEFAULT_THINKING : undefined,
            providerOptions: REASONING_OPTIONS[provider],
            openrouterReasoning: provider === 'rerun' || provider === 'openrouter' ? REASONING_REQUEST : undefined,
        }
        expect(thinkingSettingsFor(provider, 'm', null)).toEqual(expected)
        expect(thinkingSettingsFor(provider, 'm', undefined)).toEqual(expected)
    })

    it('keeps the Claude default literal', () => {
        expect(CLAUDE_DEFAULT_THINKING).toEqual({ type: 'adaptive', display: 'summarized' })
    })

    it.each(LEVELS)('maps %s per supported provider', (level) => {
        expect(thinkingSettingsFor('claude', 'm', level)).toEqual({ claudeThinking: { ...CLAUDE_DEFAULT_THINKING, effort: level } })
        expect(thinkingSettingsFor('anthropic', 'm', level)).toEqual({ providerOptions: { anthropic: { thinking: CLAUDE_DEFAULT_THINKING, effort: level } } })
        expect(thinkingSettingsFor('openai', 'm', level)).toEqual({ providerOptions: { openai: { reasoningSummary: 'auto', reasoningEffort: level } } })
        expect(thinkingSettingsFor('google', 'm', level)).toEqual({ providerOptions: { google: { thinkingConfig: { includeThoughts: true, thinkingLevel: level } } } })
        for (const p of ['openrouter', 'rerun'] as const) {
            expect(thinkingSettingsFor(p, 'm', level)).toEqual({ openrouterReasoning: { ...REASONING_REQUEST, effort: level } })
        }
    })

    it.each(['codex', 'opencode', 'custom'] as const)('unsupported %s returns the null result', (provider) => {
        for (const level of [null, ...LEVELS]) expect(thinkingSettingsFor(provider, 'm', level)).toEqual(thinkingSettingsFor(provider, 'm', null))
        expect(thinkingSettingsFor(provider, 'm', 'high')).toEqual({ providerOptions: undefined })
    })
})
