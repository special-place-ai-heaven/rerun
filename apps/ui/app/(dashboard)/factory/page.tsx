'use client'

import { useCallback, useEffect, useState } from 'react'

import { readFactorySnapshotAction } from '@/app/api/_actions/factory.actions'
import { FactoryWorld } from '@/components/factory/FactoryWorld'
import { sceneFromSnapshot } from '@/components/factory/from-snapshot'

const POLL_MS = 30_000

type Answer = Awaited<ReturnType<typeof readFactorySnapshotAction>>

// The live Factory. Without a picture yet (no answer, or the read refused) the sample loop plays.
export default function FactoryPage() {
    const [answer, setAnswer] = useState<Answer>(null)

    useEffect(() => {
        let alive = true
        const read = () => {
            readFactorySnapshotAction()
                .then(next => { if (alive && next) setAnswer(next) })
                .catch(() => {})
        }
        read()
        const id = setInterval(read, POLL_MS)
        return () => {
            alive = false
            clearInterval(id)
        }
    }, [])

    const snapshot = answer?.snapshot
    const scene = useCallback((_: number, now: number) => sceneFromSnapshot(snapshot!, now), [snapshot])

    return <FactoryWorld {...(snapshot ? { scene } : {})} />
}
