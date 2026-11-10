import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('ai', () => ({ generateText: vi.fn() }))
vi.mock('@/lib/ai/openrouter', () => ({ openrouter: (model: string) => ({ model }), hasOpenRouterKey: vi.fn(() => true) }))

import { generateText } from 'ai'
import { hasOpenRouterKey } from '@/lib/ai/openrouter'
import { proposeBoxNames } from './propose-boxes'

function modelAnswers(text: string) {
    vi.mocked(generateText).mockResolvedValue({ text } as Awaited<ReturnType<typeof generateText>>)
}

beforeEach(() => {
    vi.mocked(generateText).mockReset()
    vi.mocked(hasOpenRouterKey).mockReturnValue(true)
})

describe('proposeBoxNames', () => {
    it('hands their own words to the model', async () => {
        modelAnswers('Workshop\nShop\nClasses\nAdmin')
        await proposeBoxNames('  Pottery studio ')
        const { prompt } = vi.mocked(generateText).mock.calls[0][0] as { prompt: string }
        expect(prompt).toContain('"Pottery studio"')
    })

    it('reads a list however it is marked, and clamps it', async () => {
        modelAnswers('1. Workshop\n- **Shop**\n* "Classes",\n• Admin\nshop\nWholesale\nEvents\nPersonal')
        expect(await proposeBoxNames('Pottery studio')).toEqual(['Workshop', 'Shop', 'Classes', 'Admin', 'Wholesale', 'Events'])
    })

    it('gives up on an answer with too few team names in it', async () => {
        modelAnswers('Sure! Here are some ideas for your pottery business: workshops and a shop.')
        expect(await proposeBoxNames('Pottery studio')).toBeNull()
    })

    it('gives up on a failed or timed out call rather than throwing', async () => {
        vi.mocked(generateText).mockRejectedValue(new Error('TimeoutError'))
        expect(await proposeBoxNames('Pottery studio')).toBeNull()
    })

    it('does not call out at all without a key or without words', async () => {
        expect(await proposeBoxNames('   ')).toBeNull()
        vi.mocked(hasOpenRouterKey).mockReturnValue(false)
        expect(await proposeBoxNames('Pottery studio')).toBeNull()
        expect(generateText).not.toHaveBeenCalled()
    })
})
