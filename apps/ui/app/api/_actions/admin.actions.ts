'use server'

import { getAdminEmail } from '@/lib/auth/admin'

// Whether the signed-in caller is Rerun staff, decided from the session cookie and the server's own
// list: the browser is told the answer, never the list, which a public image must not carry.
export async function isAdminAction(): Promise<boolean> {
    return (await getAdminEmail()) !== null
}
