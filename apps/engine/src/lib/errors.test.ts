import { describe, expect, it } from 'vitest'
import { HttpError, agentDisabled, badRequest, notFound, unauthorized } from './errors.js'

describe('HttpError', () => {
    it('is an Error with a status and its own name', () => {
        const err = new HttpError(418, 'teapot')
        expect(err).toBeInstanceOf(Error)
        expect(err.status).toBe(418)
        expect(err.message).toBe('teapot')
        expect(err.name).toBe('HttpError')
    })
})

describe('error factories', () => {
    it.each([
        [notFound('Agent'), 404, 'Agent not found'],
        [badRequest('bad input'), 400, 'bad input'],
        [unauthorized(), 401, 'Unauthorized'],
        [unauthorized('Invalid token'), 401, 'Invalid token'],
        [agentDisabled(), 403, 'This coworker is switched off and cannot run.'],
    ])('%s has status %i', (err, status, message) => {
        expect(err).toBeInstanceOf(HttpError)
        expect(err.status).toBe(status)
        expect(err.message).toBe(message)
    })
})
