import type { ForemanIntakeRequest } from './foreman.js'
import { TEMPLATE_CATEGORIES, type TemplateCategory } from './template-display.js'
import { TRIAL_ACTIVE_AGENTS } from './billing.js'

// The welcome card of the onboarding, asked the same way on the web and in the app: its questions,
// their order and the lists under them. Pure, so both clients and their labs replay it without a network.

// The kind of company comes first, always: it is what decides the teams on the board, and a site
// only says what a company sells, never what its founder means to build.
export const INTAKE_STEPS = ['industry', 'company', 'role', 'name'] as const

export type IntakeStep = (typeof INTAKE_STEPS)[number]

export type IntakeDraft = {
    companyUrl: string
    /** They passed on the site. */
    websiteSkipped: boolean
    /** Picked from the list. `null` until they pick, or while they write their own under "Other". */
    industry: IntakeKind | null
    /** Typed under "Other", the line of business we had no bucket for. */
    industryLabel: string
    position: string
    firstName: string
}

export const EMPTY_DRAFT: IntakeDraft = { companyUrl: '', websiteSkipped: false, industry: null, industryLabel: '', position: '', firstName: '' }

// A title that is the question, a line under it that says why it is asked: the only thing that sets
// a form apart from a conversation.
export const INTAKE_COPY: Record<IntakeStep, { title: string; description: string }> = {
    industry: { title: 'What kind of company are you building?', description: 'It decides which teams we put on your board.' },
    company: { title: 'What is your company website?', description: 'We read it to learn what you sell and who you sell to.' },
    role: { title: 'And what do you do there?', description: 'It decides who gets built for you first.' },
    name: { title: 'Last one: your first name?', description: 'So we are not talking to a workspace.' },
}

/**
 * The questions actually asked. A Google sign-up already carries a first name, and asking someone
 * their own name when it is written in the header is the one question that reads as a form.
 */
export function intakeSteps(knownFirstName: string | null | undefined): IntakeStep[] {
    return INTAKE_STEPS.filter(step => step !== 'name' || !knownFirstName?.trim())
}

/** Whether a step has something in it, which is what the stepper's dots read. */
export function stepAnswered(step: IntakeStep, draft: IntakeDraft): boolean {
    if (step === 'company') return !!draft.companyUrl.trim() || draft.websiteSkipped
    if (step === 'industry') return !!draft.industry || !!draft.industryLabel.trim()
    if (step === 'role') return !!draft.position.trim()
    return !!draft.firstName.trim()
}

/** The furthest step that can be opened: every step before it is answered. */
export function furthestReachable(steps: IntakeStep[], draft: IntakeDraft): number {
    const firstUnanswered = steps.findIndex(step => !stepAnswered(step, draft))
    return firstUnanswered === -1 ? steps.length - 1 : firstUnanswered
}

/** `boxes`: the teams proposed for what they wrote under "Other", which the board has been drawing. */
export function toIntake(draft: IntakeDraft, knownFirstName: string | null | undefined, decided: TemplateCategory | null = null, boxes: string[] | null = null): ForemanIntakeRequest {
    const trim = (value: string) => value.trim() || null
    return {
        companyUrl: trim(draft.companyUrl),
        industry: draft.industry,
        decidedIndustry: decided,
        industryLabel: trim(draft.industryLabel),
        position: trim(draft.position),
        firstName: trim(draft.firstName) ?? (knownFirstName?.trim() || null),
        boxes,
    }
}

/**
 * What the fast decision should be asked about: nothing once a kind is picked, their own words when
 * they wrote one under "Other", and the site only when they said nothing of the kind at all. A site
 * never overrides the kind someone chose.
 */
export function industryHint(draft: IntakeDraft): string | null {
    if (draft.industry) return null
    return draft.industryLabel.trim() || draft.companyUrl.trim() || null
}

export function isTemplateCategory(value: string): value is TemplateCategory {
    return (TEMPLATE_CATEGORIES as readonly string[]).includes(value)
}

// Someone building software products and prototypes of every sort, rather than running one SaaS.
// Not a template category: the library has no shelf for it and the templates that fit are the SaaS
// ones, so it is filed under `saas` for everything the catalogue reads, and only its teams differ.
export const SOFTWARE_STUDIO = 'studio'

/** What the first question answers: a template category, or the one kind the library has no shelf for. */
export type IntakeKind = TemplateCategory | typeof SOFTWARE_STUDIO

export const INTAKE_KINDS = [...TEMPLATE_CATEGORIES, SOFTWARE_STUDIO] as const

export function isIntakeKind(value: string): value is IntakeKind {
    return value === SOFTWARE_STUDIO || isTemplateCategory(value)
}

/** The category a kind is filed under, which is what the catalogue, the tools and the profile read. */
export function kindCategory(kind: IntakeKind): TemplateCategory {
    return kind === SOFTWARE_STUDIO ? 'saas' : kind
}

// `other` is not offered: it is the bucket a site falls into, never a business someone recognises
// themselves in. The card's free field is what covers it, and what they type there is classified.
// The studio comes first: it is who builds on Rerun today.
export const INTAKE_INDUSTRIES: { value: IntakeKind }[] = [{ value: SOFTWARE_STUDIO }, ...TEMPLATE_CATEGORIES.filter(category => category !== 'other').map(category => ({ value: category }))]

// The roles offered under the role question. Hand written per industry, same reasoning as
// INDUSTRY_BOX_NAMES: the point is that someone recognises their own job in four lines, and a list
// derived from a capability taxonomy never does that. The owner comes first everywhere, because it
// is who signs up, and the card's free field carries everyone else.
export const INDUSTRY_ROLES: Record<IntakeKind, string[]> = {
    studio: ['Founder / Builder', 'Engineer or developer', 'Designer', 'Product or project lead'],
    agencies: ['Founder / Agency owner', 'Account or client lead', 'Marketing / Creative', 'Operations'],
    ecommerce: ['Founder / Store owner', 'Marketing / Growth', 'Customer care', 'Operations / Logistics'],
    saas: ['Founder / CEO', 'Product or Engineering', 'Marketing / Growth', 'Sales or Support'],
    sales: ['Founder / CEO', 'Sales rep or AE', 'Sales leadership', 'Marketing / Demand gen'],
    recruiting: ['Founder / Agency owner', 'Recruiter', 'Talent or HR lead', 'Operations'],
    'real-estate': ['Founder / Broker', 'Agent', 'Property or portfolio manager', 'Marketing'],
    legal: ['Founder / Partner', 'Lawyer or counsel', 'Paralegal or legal ops', 'Business development'],
    creators: ['Creator / Founder', 'Editor or writer', 'Community or social', 'Sponsorships / Business'],
    productivity: ['Founder / CEO', 'Operations', 'Finance or Admin', 'Project or team lead'],
    other: [],
}

// Someone whose industry says nothing, or who skipped the question: the four that read as separate
// jobs whatever the business.
export const DEFAULT_ROLES = ['Founder / CEO', 'Marketing', 'Sales', 'Operations']

// Takes a plain string, not a `TemplateCategory`: the answer may come back out of a jsonb column or
// straight off a card, including a label a later revision of the list drops.
export function rolesForIndustry(industry: string | null | undefined): string[] {
    if (!industry || !isIntakeKind(industry) || INDUSTRY_ROLES[industry].length === 0) return DEFAULT_ROLES
    return INDUSTRY_ROLES[industry]
}

// Whether what has been typed so far is worth spending a read on. Deliberately not the server's own
// check: this runs on every keystroke, and the server checks again anyway.
const SITE = /^(https?:\/\/)?[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}(\/.*)?$/i

export function looksLikeSite(input: string): boolean {
    return SITE.test(input.trim())
}

// How many coworkers the starter pack lets them pick: the ones a trial runs at once.
export const MAX_STARTER_PICKS = TRIAL_ACTIVE_AGENTS
