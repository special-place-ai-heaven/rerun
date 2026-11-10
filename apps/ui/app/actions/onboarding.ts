import type { WorkType } from '@/lib/onboarding/work-types'
import type { TemplateCategory } from '@rerun/contracts'

// The shape of `workspace_onboarding.answers`, written by the foreman's save_profile and read by the
// naming service, the lifecycle emails and the template recommender.
//
// Every field is optional, and the ones nothing asks any more are still declared: rows written
// before it was recalibrated carry a `use_case` pivot that no longer exists, then an industry and a
// role the two-step version dropped, then the work type the website question replaced. Reading one
// back must not claim fields it never had.
export type OnboardingAnswers = {
    // What the company website step read off the site, when it was given and could be read.
    company_url?: string
    company_name?: string
    company_description?: string
    company_offering?: string
    company_audience?: string
    industry?: TemplateCategory
    // The Boxes the welcome card laid out when they are not their industry's own: a software studio's,
    // or the ones proposed for the kind of company they described under "Other".
    boxes?: string[]
    // Service slugs, in the order they were picked.
    tools?: string[]
    // Answered "later" rather than answered: kept so the survey never asks twice, and so the
    // funnel can tell an empty profile apart from a deliberate pass.
    skipped?: boolean
    // Written by earlier versions of the survey, still read for users who onboarded back then.
    work_type?: WorkType | 'other'
    work_type_other?: string
    sector?: TemplateCategory
    company_size?: string
    position?: string
    position_other?: string
}
