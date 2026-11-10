'use client'

import type { IntakeKind, TemplateCategory } from '@rerun/contracts'
import { useTranslations } from 'next-intl'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { intakePreviewPlan, looksLikeSite, type ForemanIntake } from '@/lib/onboarding/intake'
import { useForemanStore } from '@/stores/foreman.store'
import { EMPTY_DRAFT, furthestReachable, intakeSteps, stepAnswered, toIntake, type IntakeDraft, type IntakeStep } from './steps'

// The card, wired: which question is on screen, what the board is drawing behind it, and the one
// write at the end.
//
// Nothing is persisted along the way. The whole card is twenty seconds and writes nothing until it
// is done, so a reload simply asks again rather than resuming half a profile.

// Assez court pour que l'aperçu arrive pendant la question suivante, assez long pour qu'une adresse
// tapée lettre par lettre ne parte pas à chaque domaine intermédiaire qu'elle traverse.
const TYPING_PAUSE_MS = 350

export type ForemanIntakeHandlers = {
    /** The fast industry decision, off a site or off their own words. `null` = we could not tell. */
    onDecideIndustry: (input: string) => Promise<TemplateCategory | null>
    /** The teams for the kind of company they described under "Other". `null` = none could be proposed. */
    onProposeTeams: (words: string) => Promise<string[] | null>
    /** Reads the site and lays what it finds on the board, started early. Settles once the read is done. */
    onAnalyzeSite: (url: string) => Promise<unknown>
    /** `ownAsk`: the line written in the composer under the card, which cuts the questions short. */
    onSubmit: (intake: ForemanIntake, ownAsk?: string) => Promise<void>
}

export type ForemanIntakeController = {
    steps: IntakeStep[]
    step: IntakeStep
    index: number
    last: boolean
    answered: boolean[]
    /** The furthest step that can be opened, every one before it being answered. */
    reachable: number
    /** Whether the step on screen, and every one before it, is answered. */
    canAdvance: boolean
    draft: IntakeDraft
    /** The industry the board is drawing, picked or decided. */
    industry: IntakeKind | null
    deciding: boolean
    /** Where the read of the typed site stands. `null` when there is no site to read. */
    siteRead: 'reading' | 'ready' | null
    submitting: boolean
    error: string | null
    set: (patch: Partial<IntakeDraft>) => void
    /** Picks an industry off the list and moves on, the way a single choice answers itself. */
    chooseIndustry: (industry: IntakeKind) => void
    /** Picks a role off the list and moves on, or sends the card when the role is its last question. */
    chooseRole: (position: string) => void
    /** Passes on the site and moves on. */
    skipWebsite: () => void
    goTo: (index: number) => void
    back: () => void
    next: () => void
    /**
     * Sends what is answered so far with the line written in the composer, the rest left unasked.
     * `false`: nothing left, the line is the caller's to give back.
     */
    sendOwn: (ownAsk: string) => boolean
}

export function useForemanIntake({ firstName, handlers }: { firstName: string | null; handlers: ForemanIntakeHandlers }): ForemanIntakeController {
    const t = useTranslations('foreman.intake')
    const [index, setIndex] = useState(0)
    const [draft, setDraft] = useState<IntakeDraft>(EMPTY_DRAFT)
    const steps = useMemo(() => intakeSteps(firstName), [firstName])
    const [decided, setDecided] = useState<TemplateCategory | null>(null)
    // The teams proposed for the words they wrote under "Other", and for which words: an answer that
    // came back for words they have since rewritten is not theirs anymore.
    const [proposal, setProposal] = useState<{ words: string; boxes: string[] | null } | null>(null)
    const [deciding, setDeciding] = useState(false)
    const [readFor, setReadFor] = useState<string | null>(null)
    const [submitting, setSubmitting] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Only the latest input may land: a decision for a site they have since changed would repaint the
    // board under them. A picked industry needs no token, it wins over `decided` on its own.
    const race = useRef(0)
    // What has already been sent, so the debounce, the Next button and a step revisited on the way
    // back do not pay for the same address three times.
    const sent = useRef<string | null>(null)
    const proposing = useRef(0)
    const proposed = useRef<string | null>(null)
    // Kept in a ref rather than read from the closures below: the callbacks are rebuilt on every
    // render of the column, and a `useCallback` that depended on them would rebuild with them, which
    // the step machine has no reason to do. Same reasoning as the gates of useForemanChat.
    const handlersRef = useRef(handlers)
    useEffect(() => {
        handlersRef.current = handlers
    }, [handlers])

    const industry = draft.industry ?? decided
    const reachable = furthestReachable(steps, draft)
    const canAdvance = reachable > index || steps.every(step => stepAnswered(step, draft))
    // Their own words under "Other", the one answer whose teams no list holds.
    const words = draft.industry ? '' : draft.industryLabel.trim()
    const teamsSettled = !!words && proposal?.words === words
    const teams = teamsSettled ? (proposal?.boxes ?? null) : null
    // Said what kind of company it is, picked or in their own words: the site is then only read.
    const kindGiven = !!draft.industry || !!words

    // The divisions on the board follow the kind and nothing else, so picking one repaints
    // immediately and a decision landing repaints once. Their own words wait for their teams, and
    // fall back on the universal divisions when none came.
    const setIntakePreview = useForemanStore(state => state.setIntakePreview)
    useEffect(() => {
        if (words) {
            if (teamsSettled) setIntakePreview(intakePreviewPlan(null, teams))
            return
        }
        if (!industry) return
        setIntakePreview(intakePreviewPlan(industry))
    }, [industry, words, teamsSettled, teams, setIntakePreview])

    // Typing a site answers the site question only: the kind they chose stays theirs.
    const set = useCallback((patch: Partial<IntakeDraft>) => {
        setError(null)
        const bySite = patch.companyUrl?.trim() ? { websiteSkipped: false } : null
        setDraft(current => ({ ...current, ...patch, ...bySite }))
    }, [])

    const decide = useCallback((input: string) => {
        if (sent.current === input) return
        sent.current = input
        const token = (race.current += 1)
        setDeciding(true)
        void handlersRef.current
            .onDecideIndustry(input)
            .then(found => {
                if (race.current !== token) return
                setDecided(found)
            })
            .catch(() => {})
            .finally(() => {
                if (race.current !== token) return
                setDeciding(false)
            })
    }, [])

    const propose = useCallback((input: string) => {
        if (proposed.current === input) return
        proposed.current = input
        const token = (proposing.current += 1)
        void handlersRef.current
            .onProposeTeams(input)
            .catch(() => null)
            .then(boxes => {
                if (proposing.current === token) setProposal({ words: input, boxes })
            })
    }, [])

    const analyze = useCallback((url: string) => {
        void handlersRef.current
            .onAnalyzeSite(url)
            .catch(() => {})
            .finally(() => setReadFor(url))
    }, [])

    // Une adresse est lisible bien avant qu'on ait fini de répondre, et l'industrie décide de ce que
    // le board dessine : attendre le bouton Next, c'est perdre la seule seconde où l'aperçu pouvait
    // arriver avant la question suivante. On part dès que la frappe s'arrête et que ce qui est écrit
    // ressemble à un site, puis Next ne renvoie que ce qui n'est pas déjà parti.
    // Le métier, lui, n'est décidé sur le site que si rien n'a été dit du genre d'entreprise.
    const site = draft.companyUrl.trim()
    const readable = looksLikeSite(site) ? site : null
    useEffect(() => {
        if (!readable) return
        const timer = setTimeout(() => {
            analyze(readable)
            if (!kindGiven) decide(readable)
        }, TYPING_PAUSE_MS)
        return () => clearTimeout(timer)
    }, [readable, kindGiven, analyze, decide])

    // Passer sur le site ne touche pas au genre d'entreprise déjà répondu, ni à ce qui en a été décidé.
    const skipWebsite = useCallback(() => {
        if (submitting) return
        setError(null)
        setDraft(current => ({ ...current, companyUrl: '', websiteSkipped: true }))
        setIndex(index + 1)
    }, [index, submitting])

    // Écrit le choix et avance dans le même geste : un `next()` appelé derrière verrait encore le
    // draft d'avant, où la question n'a pas de réponse.
    const chooseIndustry = useCallback(
        (picked: IntakeKind) => {
            if (submitting) return
            setError(null)
            setDraft(current => ({ ...current, industry: picked, industryLabel: '' }))
            setIndex(index + 1)
        },
        [index, submitting]
    )

    const submit = useCallback(
        (value: IntakeDraft, decidedIndustry: TemplateCategory | null, ownAsk?: string) => {
            // A proposal still on its way would repaint the board over the teams the server writes.
            proposing.current += 1
            setSubmitting(true)
            setError(null)
            void handlersRef.current
                .onSubmit(toIntake(value, firstName, decidedIndustry, teams), ownAsk)
                .catch(() => setError(t('saveFailed')))
                .finally(() => setSubmitting(false))
        },
        [firstName, t, teams]
    )

    const chooseRole = useCallback(
        (position: string) => {
            if (submitting) return
            setError(null)
            const chosen = { ...draft, position }
            setDraft(chosen)
            if (index < steps.length - 1) {
                setIndex(index + 1)
                return
            }
            submit(chosen, decided)
        },
        [decided, draft, index, steps, submit, submitting]
    )

    const goTo = useCallback(
        (target: number) => {
            if (submitting) return
            setIndex(Math.min(Math.max(target, 0), reachable))
        },
        [reachable, submitting]
    )

    const next = useCallback(() => {
        if (submitting || !canAdvance) return
        // Ce que la pause de frappe n'a pas pu envoyer : la ligne tapée sous « Other », qui n'a
        // aucune forme à reconnaître, et une adresse validée à la dernière seconde.
        if (steps[index] === 'industry' && words) {
            decide(words)
            propose(words)
        }
        if (steps[index] === 'company' && readable) {
            analyze(readable)
            if (!kindGiven) decide(readable)
        }
        if (index < steps.length - 1) {
            setIndex(index + 1)
            return
        }
        submit(draft, decided)
    }, [analyze, canAdvance, decide, decided, draft, index, kindGiven, propose, readable, steps, submit, submitting, words])

    // Le site déjà tapé est gardé : c'est lui qui décrit l'entreprise au coworker écrit d'après la
    // phrase. Il part ici s'il n'était pas encore parti, comme au Next.
    const sendOwn = useCallback(
        (ownAsk: string) => {
            const asked = ownAsk.trim()
            if (submitting || !asked) return false
            if (readable) {
                analyze(readable)
                if (!kindGiven) decide(readable)
            }
            submit(draft, decided, asked)
            return true
        },
        [analyze, decide, decided, draft, kindGiven, readable, submit, submitting]
    )

    return {
        steps,
        step: steps[index],
        index,
        last: index === steps.length - 1,
        answered: steps.map(step => stepAnswered(step, draft)),
        reachable,
        canAdvance,
        draft,
        industry,
        deciding,
        siteRead: !readable ? null : readFor === readable ? 'ready' : 'reading',
        submitting,
        error,
        set,
        chooseIndustry,
        chooseRole,
        skipWebsite,
        goTo,
        back: () => goTo(index - 1),
        next,
        sendOwn,
    }
}
