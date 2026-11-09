import { describe, expect, it } from 'vitest'
import type { SupabaseClient } from '@supabase/supabase-js'
import type { Database } from '@/app/api/database.types'
import { loadFirstName, loadRecipient } from './recipient'

function withUser(user: Record<string, unknown> | null, error: unknown = null) {
    const result = { data: { user: user && { is_anonymous: false, email: 'ada@example.com', user_metadata: {}, ...user } }, error }
    return { auth: { admin: { getUserById: async () => result } } } as unknown as SupabaseClient<Database>
}

describe('loadRecipient', () => {
    it('finds nobody on a lookup error, for an anonymous visitor, or without a real address', async () => {
        expect(await loadRecipient(withUser(null, { message: 'boom' }), 'u')).toBeNull()
        expect(await loadRecipient(withUser({ is_anonymous: true }), 'u')).toBeNull()
        expect(await loadRecipient(withUser({ email: '   ' }), 'u')).toBeNull()
    })

    it('trims the address and reads the first name', async () => {
        expect(await loadRecipient(withUser({ email: ' ada@example.com ', user_metadata: { full_name: 'Ada  Lovelace' } }), 'u')).toEqual({ email: 'ada@example.com', firstName: 'Ada' })
    })
})

describe('loadFirstName', () => {
    it.each([
        [{ first_name: ' Ada ', given_name: 'Grace' }, 'Ada'],
        [{ given_name: 'Grace', full_name: 'Alan Turing' }, 'Grace'],
        [{ name: 'Linus Torvalds' }, 'Linus'],
        [{ first_name: 42, full_name: '   ' }, null],
    ])('reads the first name from %j, address or not', async (metadata, expected) => {
        expect(await loadFirstName(withUser({ email: null, user_metadata: metadata }), 'u')).toBe(expected)
    })
})
