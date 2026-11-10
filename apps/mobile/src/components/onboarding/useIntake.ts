import { EMPTY_DRAFT, industryHint, intakeSteps, stepAnswered, toIntake, type ForemanIntakeRequest, type IntakeDraft, type TemplateCategory } from '@rerun/contracts'
import { useRef, useState } from 'react'

const INDUSTRY_WAIT_MS = 2500

type IntakeOptions = {
    knownFirstName: string | null
    // The fast guess at an industry from a site, made while the next questions are being answered.
    decideIndustry: (input: string) => Promise<TemplateCategory | null>
    submit: (intake: ForemanIntakeRequest) => Promise<void>
    initial?: Partial<IntakeDraft>
    initialIndex?: number
}

// The welcome card's state, the web card's order: the kind of company, the site, the role, then the
// first name only when nobody gave it yet. The teams of a kind typed under "Other" are proposed by the
// server when the card is saved: the app draws no board while it asks.
export function useIntake({ knownFirstName, decideIndustry, submit, initial, initialIndex = 0 }: IntakeOptions) {
    const [draft, setDraft] = useState<IntakeDraft>({ ...EMPTY_DRAFT, ...initial })
    const [index, setIndex] = useState(initialIndex)
    const [decided, setDecided] = useState<TemplateCategory | null>(null)
    const [submitting, setSubmitting] = useState(false)
    const [saveFailed, setSaveFailed] = useState(false)
    const [deciding, setDeciding] = useState(false)
    const asked = useRef(0)

    const steps = intakeSteps(knownFirstName)
    const step = steps[Math.min(index, steps.length - 1)]
    const last = index >= steps.length - 1

    // Asked as the kind typed under "Other" is left behind, so the role question offers the roles of its
    // industry rather than swapping its options under the finger. It waits a moment for the guess, then
    // falls back on the roles every business has. A site is never guessed from: the kind is asked first.
    const guessIndustry = (final: IntakeDraft) => {
        const hint = industryHint(final)
        if (!hint) return
        const ask = ++asked.current
        const settle = (industry: TemplateCategory | null) => {
            if (ask !== asked.current) return
            if (industry) setDecided(industry)
            setDeciding(false)
        }
        setDeciding(true)
        setTimeout(() => settle(null), INDUSTRY_WAIT_MS)
        decideIndustry(hint)
            .then(settle)
            .catch(() => settle(null))
    }

    const set = (patch: Partial<IntakeDraft>) => {
        setSaveFailed(false)
        setDraft(current => ({ ...current, ...patch }))
    }

    const finish = async (final: IntakeDraft) => {
        setSubmitting(true)
        try {
            await submit(toIntake(final, knownFirstName, decided))
        } catch {
            setSaveFailed(true)
            setSubmitting(false)
        }
    }

    const next = (final: IntakeDraft = draft) => {
        if (!stepAnswered(step, final) || submitting) return
        if (step === 'industry') guessIndustry(final)
        if (last) return void finish(final)
        setIndex(current => current + 1)
    }

    // A choice answers its step on the spot, as an option of a question does.
    const choose = (patch: Partial<IntakeDraft>) => {
        const final = { ...draft, ...patch }
        setDraft(final)
        next(final)
    }

    const skipWebsite = () => {
        const final = { ...draft, companyUrl: '', websiteSkipped: true }
        setDraft(final)
        setIndex(steps.indexOf('company') + 1)
    }

    const back = () => {
        setSaveFailed(false)
        if (index === 0) return
        setIndex(current => current - 1)
    }

    return { step, steps, index, draft, industry: draft.industry ?? decided, deciding, submitting, saveFailed, canAdvance: stepAnswered(step, draft), last, set, choose, next, back, skipWebsite }
}

export type IntakeController = ReturnType<typeof useIntake>
