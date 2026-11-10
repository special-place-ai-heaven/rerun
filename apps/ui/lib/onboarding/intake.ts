import { kindCategory, type IntakeKind, type TemplateCategory } from '@rerun/contracts'

import type { ShownPlan } from '@/components/foreman/widgets/plan-card'
import { DEFAULT_BOX_NAMES, divisionExamples } from '@/lib/onboarding/box-name-suggestions'

export { DEFAULT_ROLES, INDUSTRY_ROLES, INTAKE_INDUSTRIES, looksLikeSite, rolesForIndustry } from '@rerun/contracts'

// What the welcome card asks, and what it draws on the board while it asks it. Pure, so the lab can
// replay every industry without a network and the server can read the same lists back.

/** What the card hands over once its four steps are done. */
export type ForemanIntake = {
    companyUrl: string | null
    /** Picked by hand from the list. The only one of the three that is not a guess. */
    industry: IntakeKind | null
    /**
     * What the fast decision made of their address while they were still answering, and therefore
     * what the board drew. Carried so a site the full read could not reach (no key, a crawler
     * blocked) still lands an industry rather than none: without it the foreman would be told the
     * company has no line of business while five of its divisions are on screen beside it.
     */
    decidedIndustry: TemplateCategory | null
    /** What they typed under "Other", when they named an industry we have no bucket for. */
    industryLabel: string | null
    position: string | null
    firstName: string | null
    /** The teams proposed for what they typed under "Other", once the model answered. */
    boxes?: string[] | null
}

// Five is the ceiling rather than the count: `INDUSTRY_BOX_NAMES` is ordered most universal first,
// so cutting from the end drops the division someone is least likely to run.
const MAX_BOXES = 5

/**
 * The divisions drawn on the board the moment the industry is known. Never empty. `own`: the teams
 * proposed for their own words under "Other", which win over any industry's when there are some.
 */
export function intakeBoxes(industry: string | null | undefined, own?: string[] | null): string[] {
    return (own?.length ? own : (divisionExamples(industry) ?? DEFAULT_BOX_NAMES)).slice(0, MAX_BOXES)
}

/**
 * The industry an answered card is filed under, `read` being what the full read of the site made of
 * it. A kind they picked always wins, and a site never overrides it. Their own words under "Other"
 * come next, through the fast decision made of them. Only when they said nothing of the kind does
 * the full read decide, then the fast decision made of the address.
 */
export function intakeIndustry(intake: Pick<ForemanIntake, 'industry' | 'decidedIndustry' | 'industryLabel'>, read: TemplateCategory | null | undefined): TemplateCategory | null {
    if (intake.industry) return kindCategory(intake.industry)
    return (intake.industryLabel ? (intake.decidedIndustry ?? read) : (read ?? intake.decidedIndustry)) ?? null
}

/**
 * The divisions an answered card lays out: the teams proposed for their own words, the universal
 * ones when what they wrote got none, else those of the kind they picked or the site was filed under.
 */
export function boxesOfIntake(intake: Pick<ForemanIntake, 'industry' | 'decidedIndustry' | 'industryLabel' | 'boxes'>): string[] {
    if (!intake.industry && intake.industryLabel?.trim()) return intakeBoxes(null, intake.boxes)
    return intakeBoxes(intake.industry ?? intake.decidedIndustry, intake.boxes)
}

// What a proposed team may be named: one to three plain words a person would give a division, in
// any script. Nothing else gets through, since the names end up in the foreman's own instructions.
const TEAM_NAME = /^[\p{L}\p{N}][\p{L}\p{N}&' -]*$/u
const TEAM_NAME_MAX = 24
const TEAM_WORDS_MAX = 3
const MIN_TEAMS = 4
const MAX_TEAMS = 6

/**
 * The proposed teams that can go on a board, or null when fewer than four survive: a model answer
 * or a client list is read the same way. Duplicates are matched as the build matches Boxes.
 */
export function clampBoxNames(names: unknown): string[] | null {
    if (!Array.isArray(names)) return null
    const clean = names
        .map(name => (typeof name === 'string' ? name.replace(/\s+/g, ' ').trim() : ''))
        .filter(name => name.length > 0 && name.length <= TEAM_NAME_MAX && name.split(' ').length <= TEAM_WORDS_MAX && TEAM_NAME.test(name))
    const unique = clean.filter((name, index) => clean.findIndex(other => other.toLowerCase() === name.toLowerCase()) === index).slice(0, MAX_TEAMS)
    return unique.length >= MIN_TEAMS ? unique : null
}

/**
 * The same shape the foreman's own plan card hands the board, with no agent in any of it: the Boxes
 * trace themselves, and nothing pretends anyone has been hired yet. The title is dead weight here,
 * since the board no longer draws one, but it is what `ShownPlan` is, so it carries the company name.
 */
/**
 * The board of someone who arrived on a template or a shared coworker, before anything is built: the
 * default divisions, and what they came for already sitting in the first one.
 */
export function arrivalPreviewPlan(title: string): ShownPlan {
    return {
        title: 'Your company',
        groups: intakeBoxes(null).map((name, index) => ({ key: `arrival-${index}-${name}`, name, role: '', items: index === 0 ? [{ key: 'arrival', name: title, role: '', when: '' }] : [] })),
    }
}

export function intakePreviewPlan(industry: string | null | undefined, own?: string[] | null, companyName?: string | null): ShownPlan {
    return {
        title: companyName?.trim() || 'Your company',
        groups: intakeBoxes(industry, own).map((name, index) => ({ key: `intake-${index}-${name}`, name, role: '', items: [] })),
    }
}
