'use server'

import { SOFTWARE_STUDIO, type TemplateCategory } from '@rerun/contracts'

import { requireWorkspaceContext } from '@/app/api/_auth/ownership'
import { decideIndustry } from '@/lib/company/decide-industry'
import { companySiteUrl } from '@/lib/company/firecrawl'
import { analyzeCompanyProfile } from '@/lib/company/profile'
import { mergeForeman, readAnswers, saveForemanProfile, stampWorkspaceOnboarded } from '@/lib/foreman/profile'
import { takeIntakeCall } from '@/lib/onboarding/anonymous-intake-quota'
import { DEFAULT_BOX_NAMES } from '@/lib/onboarding/box-name-suggestions'
import { isTemplateCategory } from '@/lib/onboarding/industries'
import { clampBoxNames, intakeBoxes, intakeIndustry, type ForemanIntake } from '@/lib/onboarding/intake'
import { proposeBoxNames } from '@/lib/onboarding/propose-boxes'

// The welcome card's half of the onboarding: everything it needs that cannot happen in the browser.
// No model in the loop writes anything here, the card asked the four questions itself.
//
// An anonymous visitor answers the card too, so the industry decision is open to them, and the
// write is not: their answers wait in the browser until they have an account. Every workspace, with
// an account or not, decides within a quota (the read of the site goes through
// /api/onboarding/discoveries, under its own): each call is a paid model decision.

/**
 * Which industry, fast enough for the board to draw the Boxes while the card is still being filled.
 * Takes the site they typed or the sentence they wrote under "Other", and `null` means "we have no
 * idea", which the card reads as the universal divisions rather than as an error.
 */
export async function decideIndustryAction(input: string): Promise<TemplateCategory | null> {
    const ctx = await requireWorkspaceContext()
    if (!takeIntakeCall(ctx.workspace.id, 'decide')) return null
    const decision = await decideIndustry(input)
    return decision?.industry ?? null
}

/**
 * The teams for the kind of company they described under "Other", drawn on the board while they
 * answer the next question. Same quota as the decision: it is a paid model call of the same card.
 * `null` means none could be proposed, which the card reads as the universal divisions.
 */
export async function proposeBoxesAction(words: string): Promise<string[] | null> {
    const ctx = await requireWorkspaceContext()
    if (!takeIntakeCall(ctx.workspace.id, 'decide')) return null
    return proposeBoxNames(words)
}

/**
 * The Boxes to write beside the industry, when they are not that industry's own: a studio's, or the
 * ones proposed for their own words. The card sends the ones the board drew, read again here since
 * they end up in the foreman's instructions; an app build that drew none gets them proposed now.
 */
async function boxesToWrite(intake: ForemanIntake): Promise<string[] | undefined> {
    if (intake.industry === SOFTWARE_STUDIO) return intakeBoxes(SOFTWARE_STUDIO)
    const words = intake.industry ? null : intake.industryLabel?.trim()
    if (!words) return undefined
    return clampBoxNames(intake.boxes) ?? (await proposeBoxNames(words)) ?? DEFAULT_BOX_NAMES
}

/**
 * Writes the profile and closes discovery. What comes back is the industry that was actually
 * stored, so the board keeps drawing the divisions the foreman is about to be told about, even when
 * the full analysis disagreed with the fast decision at the last second.
 */
export async function saveForemanIntakeAction(intake: ForemanIntake): Promise<{ industry: TemplateCategory | null; boxes: string[] | null }> {
    const ctx = await requireWorkspaceContext()
    if (ctx.authUser.is_anonymous) throw new Error('Create your account first.')

    const url = intake.companyUrl ? companySiteUrl(intake.companyUrl) : null
    // Free by now in the common case: the board's discoveries started this read three questions ago
    // and the module caches it for fifteen minutes.
    const analysis = url ? await analyzeCompanyProfile(url) : null
    const profile = analysis?.ok ? analysis.analysis.profile : null

    // A kind they picked themselves always wins, a site never overrides it (intakeIndustry).
    const industry = intakeIndustry(intake, profile?.industry)
    const boxes = await boxesToWrite(intake)

    await saveForemanProfile(ctx, {
        company_url: analysis?.ok ? analysis.analysis.url : (url ?? undefined),
        company_name: profile?.name,
        company_description: profile?.description,
        // What they typed under "Other" is the only thing they said about their line of business, so
        // it is kept verbatim beside the bucket it was filed into.
        company_offering: profile?.offering ?? intake.industryLabel ?? undefined,
        company_audience: profile?.audience,
        industry: industry ?? undefined,
        boxes,
        position: intake.position ?? undefined,
        first_name: intake.firstName ?? undefined,
    })

    return { industry: industry && isTemplateCategory(industry) ? industry : null, boxes: boxes ?? null }
}

/**
 * Closes the onboarding of a workspace that installed what it arrived on without ever showing it the
 * welcome card. The coworker's own chat is already asking what it needs, so the profile the card
 * would have asked for is given up rather than owed forever.
 */
export async function waiveForemanProfileAction(): Promise<void> {
    const ctx = await requireWorkspaceContext()
    if (ctx.authUser.is_anonymous) throw new Error('Create your account first.')

    const { foreman } = await readAnswers(ctx)
    if (!foreman?.installedFirst || foreman.profileAt) return

    await mergeForeman(ctx, { installedFirst: false })
    await stampWorkspaceOnboarded(ctx)
}
