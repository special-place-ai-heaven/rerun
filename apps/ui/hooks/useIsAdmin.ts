'use client'

import { useSession } from '@/supabase/session/SessionProvider'

// Answered by the server for the signed-in account (see SessionProvider): false until it has.
export function useIsAdmin(): boolean {
    return useSession().isAdmin === true
}
