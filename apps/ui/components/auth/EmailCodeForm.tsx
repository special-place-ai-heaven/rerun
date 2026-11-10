'use client'

import { isSlowSend, SLOW_SEND_MESSAGE } from '@/components/auth/email-send'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Form, FormControl, FormField, FormItem, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { InputOTP, InputOTPGroup, InputOTPSlot } from '@/components/ui/input-otp'
import { TooltipDisabledReason } from '@/components/ui/tooltip'
import { normalizeEmail } from '@/lib/email'
import { AlertTriangle } from '@/lib/icons'
import { zodResolver } from '@hookform/resolvers/zod'
import { getCookie, setSharedCookie, track } from '@rerun/analytics/client'
import { StepTransition } from '@rerun/ui/steps'
import { REGEXP_ONLY_DIGITS } from 'input-otp'
import { useEffect, useState, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

export type EmailCodeStep = 'email' | 'code'

// `change` is the same two steps for an account that is already signed in and moves to a new
// address: nothing of it is a signup, and the button its email would carry leads nowhere.
export type EmailCodePurpose = 'sign-in' | 'change'

export const SIGN_IN_CODE_LENGTH = 6
// Supabase refuses a second code for the same address within a minute (auth.email.max_frequency).
const RESEND_COOLDOWN_SECONDS = 60

export type EmailSendOutcome = 'held' | void

const emailSchema = z.object({ email: z.string().trim().email('Enter a valid email') })
const codeSchema = z.object({ code: z.string().length(SIGN_IN_CODE_LENGTH, `Enter the ${SIGN_IN_CODE_LENGTH}-digit code`) })

function markVerificationSent() {
    track('email_verification_sent', {})
    setSharedCookie('rr_verif_sent_at', String(Date.now()), 1)
}

function markVerificationCompleted() {
    const sentAt = Number(getCookie('rr_verif_sent_at'))
    track('email_verification_completed', { via: 'code', delay_seconds: sentAt ? Math.round((Date.now() - sentAt) / 1000) : undefined })
}

const errorMessage = (error: unknown) => (error instanceof Error ? error.message : 'Something went wrong. Please try again.')

// Supabase answers a wrong code and an expired one with the same error, so the copy covers both.
const isInvalidCode = (error: unknown) => error instanceof Error && /expired|invalid/i.test(error.message)

// Passwordless sign-in: an email, then the code mailed to it. The email also carries a button that
// signs in on its own through /auth/confirm, so this form is only one of the two ways through.
export function EmailCodeForm({
    defaultEmail = '',
    sendCode,
    verifyCode,
    onStepChange,
    beforeEmail,
    purpose = 'sign-in',
    initialSentTo,
}: {
    defaultEmail?: string
    // `held`: the last code left less than a minute ago, so none was mailed.
    sendCode: (email: string) => Promise<EmailSendOutcome>
    verifyCode: (email: string, code: string) => Promise<void>
    onStepChange?: (step: EmailCodeStep) => void
    beforeEmail?: ReactNode
    purpose?: EmailCodePurpose
    initialSentTo?: string
}) {
    const [step, setStep] = useState<EmailCodeStep>(initialSentTo ? 'code' : 'email')
    const [email, setEmail] = useState(initialSentTo ?? '')
    const signingIn = purpose === 'sign-in'
    const [cooldown, setCooldown] = useState(0)
    const [resending, setResending] = useState(false)

    const emailForm = useForm<z.infer<typeof emailSchema>>({ resolver: zodResolver(emailSchema), defaultValues: { email: defaultEmail } })
    const codeForm = useForm<z.infer<typeof codeSchema>>({ resolver: zodResolver(codeSchema), defaultValues: { code: '' } })

    useEffect(() => {
        if (cooldown <= 0) return
        const timer = setTimeout(() => setCooldown(c => c - 1), 1000)
        return () => clearTimeout(timer)
    }, [cooldown])

    const goTo = (next: EmailCodeStep) => {
        setStep(next)
        onStepChange?.(next)
    }

    const submitEmail = emailForm.handleSubmit(
        async values => {
            if (signingIn) track('signup_method_selected', { method: 'email' })
            const normalized = normalizeEmail(values.email)
            const toCodeStep = () => {
                setEmail(normalized)
                codeForm.reset({ code: '' })
                setCooldown(RESEND_COOLDOWN_SECONDS)
                goTo('code')
            }
            try {
                await sendCode(normalized)
                if (signingIn) markVerificationSent()
                toCodeStep()
            } catch (error) {
                if (isSlowSend(error)) {
                    toast.info(SLOW_SEND_MESSAGE)
                    toCodeStep()
                } else {
                    toast.error(errorMessage(error))
                }
            }
        },
        errors => {
            if (signingIn && errors.email?.type) track('signup_field_error', { field: 'email', error_type: String(errors.email.type) })
        },
    )

    const submitCode = codeForm.handleSubmit(async ({ code }) => {
        try {
            await verifyCode(email, code)
            if (signingIn) markVerificationCompleted()
        } catch (error) {
            if (signingIn) track('signup_field_error', { field: 'code', error_type: errorMessage(error) })
            codeForm.setError('code', { message: isInvalidCode(error) ? 'This code is wrong or has expired.' : errorMessage(error) })
        }
    })

    const resend = async () => {
        setResending(true)
        try {
            const outcome = await sendCode(email)
            if (signingIn) markVerificationSent()
            codeForm.reset({ code: '' })
            setCooldown(RESEND_COOLDOWN_SECONDS)
            toast.success(outcome === 'held' ? 'Your last code left less than a minute ago. Check your inbox and spam folder.' : 'We sent the code again')
        } catch (error) {
            if (isSlowSend(error)) {
                setCooldown(RESEND_COOLDOWN_SECONDS)
                toast.info(SLOW_SEND_MESSAGE)
            } else {
                toast.error(errorMessage(error))
            }
        } finally {
            setResending(false)
        }
    }

    const changeEmail = () => {
        emailForm.reset({ email })
        goTo('email')
    }

    return (
        <StepTransition stepKey={step} direction={step === 'code' ? 1 : -1}>
            {step === 'email' ? (
                <div className="space-y-4">
                    {beforeEmail}
                    <Form {...emailForm}>
                        <form onSubmit={submitEmail} className="space-y-4">
                            <FormField
                                control={emailForm.control}
                                name="email"
                                render={({ field }) => (
                                    <FormItem>
                                        <FormControl>
                                            <Input type="email" label="Email" placeholder="you@rerun.build" autoComplete="email" {...field} />
                                        </FormControl>
                                        <FormMessage />
                                    </FormItem>
                                )}
                            />
                            <Button type="submit" className="w-full" loading={emailForm.formState.isSubmitting}>
                                {signingIn ? 'Continue with email' : 'Send code'}
                            </Button>
                        </form>
                    </Form>
                </div>
            ) : (
                <Form {...codeForm}>
                    <form onSubmit={submitCode} className="space-y-4">
                        <p className="text-sm text-muted-foreground">
                            We sent a {SIGN_IN_CODE_LENGTH}-digit code to <span className="font-medium text-foreground">{email}</span>. Enter it below
                            {signingIn && ', or use the button in the email'}.
                        </p>
                        <FormField
                            control={codeForm.control}
                            name="code"
                            render={({ field }) => (
                                <FormItem className="flex flex-col items-center">
                                    <FormControl>
                                        <InputOTP
                                            maxLength={SIGN_IN_CODE_LENGTH}
                                            pattern={REGEXP_ONLY_DIGITS}
                                            autoComplete="one-time-code"
                                            autoFocus
                                            disabled={codeForm.formState.isSubmitting}
                                            {...field}
                                            onComplete={() => submitCode()}
                                        >
                                            <InputOTPGroup>
                                                {Array.from({ length: SIGN_IN_CODE_LENGTH }, (_, index) => (
                                                    <InputOTPSlot key={index} index={index} />
                                                ))}
                                            </InputOTPGroup>
                                        </InputOTP>
                                    </FormControl>
                                    <FormMessage />
                                </FormItem>
                            )}
                        />
                        <Alert variant="warning" beam={false}>
                            <AlertTriangle />
                            <AlertDescription>Not in your inbox? Check your spam or promotions folder.</AlertDescription>
                        </Alert>
                        <Button type="submit" className="w-full" loading={codeForm.formState.isSubmitting}>
                            Continue
                        </Button>
                        <div className="flex items-center justify-between text-sm text-muted-foreground">
                            <button type="button" onClick={changeEmail} className="transition-colors hover:text-foreground">
                                Use a different email
                            </button>
                            <TooltipDisabledReason reason={cooldown > 0 ? `You can ask for a new code in ${cooldown}s` : undefined}>
                                <button
                                    type="button"
                                    onClick={resend}
                                    disabled={cooldown > 0 || resending}
                                    className="transition-colors hover:text-foreground disabled:pointer-events-none disabled:opacity-50"
                                >
                                    {cooldown > 0 ? `Resend code (${cooldown}s)` : 'Resend code'}
                                </button>
                            </TooltipDisabledReason>
                        </div>
                    </form>
                </Form>
            )}
        </StepTransition>
    )
}
