'use client'

import { attachServerManuallyAction, createPairingTokenAction, detachServerAction, getWorkspaceServerAction } from '@/app/api/_actions/servers.actions'
import type { WorkspaceServer } from '@/app/api/_services/servers.service'
import { ConfirmDialog } from '@/components/dialogs/ConfirmDialog'
import { CopyBlock } from '@/components/dialogs/CopyBlock'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { PanelRow } from '@/components/ui/panel-row'
import { SkeletonList } from '@/components/ui/skeleton'
import { APP_URL } from '@/lib/app-url'
import { Loader2Icon, ServerIcon } from '@/lib/icons'
import { Badge, ScrollFade } from '@rerun/ui/primitives'
import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { toast } from 'sonner'

// The engine image this fork publishes (.github/workflows/images.yml), the one docker-compose.yml runs.
const ENGINE_IMAGE = 'ghcr.io/special-place-ai-heaven/rerun-engine:dev'
const POLL_MS = 3000

function SectionTitle({ children }: { children: string }) {
    return <h3 className="px-1 text-xs font-semibold tracking-wide text-muted-foreground uppercase">{children}</h3>
}

function pairCommand(token: string, address: string): string {
    const lines = [
        'docker run -d --name rerun-engine --restart unless-stopped \\',
        '  -p 3000:3000 -v rerun-engine:/data --shm-size 2g \\',
        `  -e RERUN_HUB_URL=${APP_URL} \\`,
        `  -e RERUN_PAIR_TOKEN=${token} \\`,
        ...(address.trim() ? [`  -e RERUN_PUBLIC_URL=${address.trim()} \\`] : []),
        `  ${ENGINE_IMAGE}`,
    ]
    return lines.join('\n')
}

function ServerRow({ server, onRemove }: { server: WorkspaceServer; onRemove: () => void }) {
    const meta = server.health.reachable ? (
        <Badge tone="green" size="xs" glow={false}>
            Connected
        </Badge>
    ) : (
        <Badge tone="red" size="xs" glow={false}>
            Unreachable
        </Badge>
    )
    const description = server.health.reachable ? `${server.address} · ${server.health.activeAgents} coworkers running${server.health.commit ? ` · ${server.health.commit.slice(0, 7)}` : ''}` : `${server.address} · the app cannot reach it right now`

    return (
        <PanelRow
            leading={<ServerIcon className="size-4 shrink-0 text-muted-foreground" />}
            title="This workspace's server"
            meta={meta}
            description={description}
            actions={
                server.removable && (
                    <Button variant="outline" size="sm" onClick={onRemove}>
                        Remove
                    </Button>
                )
            }
        />
    )
}

function Pairing({ onConnected }: { onConnected: () => void }) {
    const [token, setToken] = useState<string | null>(null)
    const [address, setAddress] = useState('')
    const [creating, setCreating] = useState(false)
    const [manual, setManual] = useState(false)
    const [manualUrl, setManualUrl] = useState('')
    const [manualKey, setManualKey] = useState('')
    const [attaching, setAttaching] = useState(false)

    const create = async () => {
        setCreating(true)
        const result = await createPairingTokenAction()
        setCreating(false)
        if (!result.ok) return toast.error(result.error)
        setToken(result.token)
    }

    const attach = async () => {
        setAttaching(true)
        const result = await attachServerManuallyAction({ url: manualUrl, apiKey: manualKey })
        setAttaching(false)
        if (!result.ok) return toast.error(result.error)
        onConnected()
    }

    if (manual) {
        return (
            <section className="min-w-0 space-y-3">
                <SectionTitle>Enter a server by hand</SectionTitle>
                <Input label="Address" placeholder="http://192.168.1.20:3000" value={manualUrl} onChange={e => setManualUrl(e.target.value)} />
                <Input label="API key" placeholder="RERUN_API_KEY of the engine" value={manualKey} onChange={e => setManualKey(e.target.value)} type="password" />
                <div className="flex flex-wrap justify-end gap-2">
                    <Button variant="ghost" onClick={() => setManual(false)}>
                        Back
                    </Button>
                    <Button onClick={attach} disabled={attaching || !manualUrl.trim() || !manualKey.trim()}>
                        {attaching && <Loader2Icon className="animate-spin" />}
                        Connect
                    </Button>
                </div>
            </section>
        )
    }

    return (
        <section className="min-w-0 space-y-3">
            <SectionTitle>Add a server</SectionTitle>
            <p className="px-1 text-sm text-muted-foreground">Your coworkers run on a machine you own. Run this on it, with Docker installed. It connects by itself.</p>
            {token ? (
                <>
                    <Input
                        label="Address the app reaches it at (optional)"
                        placeholder="http://192.168.1.20:3000"
                        value={address}
                        onChange={e => setAddress(e.target.value)}
                    />
                    <CopyBlock value={pairCommand(token, address)} label="Copy the command" />
                    <p className="flex items-center gap-2 px-1 text-xs text-muted-foreground">
                        <Loader2Icon className="size-3.5 animate-spin" />
                        Waiting for the server. The command works once, for 15 minutes.
                    </p>
                </>
            ) : (
                <div className="flex flex-wrap justify-end gap-2">
                    <Button variant="ghost" onClick={() => setManual(true)}>
                        Enter address and key
                    </Button>
                    <Button onClick={create} disabled={creating}>
                        {creating && <Loader2Icon className="animate-spin" />}
                        Add server
                    </Button>
                </div>
            )}
        </section>
    )
}

export function ServersDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
    const [server, setServer] = useState<WorkspaceServer | null>(null)
    const [loading, setLoading] = useState(true)
    const [removing, setRemoving] = useState(false)
    const [confirmRemove, setConfirmRemove] = useState(false)

    const refresh = useCallback(async () => {
        const result = await getWorkspaceServerAction()
        setLoading(false)
        if (!result.ok) return toast.error(result.error)
        setServer(result.server)
    }, [])

    useEffect(() => {
        if (!open) return
        void refresh()
        // A server started from the command attaches itself: the dialog notices on its own.
        const timer = setInterval(() => void refresh(), POLL_MS)
        return () => clearInterval(timer)
    }, [open, refresh])

    const remove = async () => {
        setRemoving(true)
        const result = await detachServerAction()
        setRemoving(false)
        setConfirmRemove(false)
        if (!result.ok) return toast.error(result.error)
        toast.success('Server removed')
        void refresh()
    }

    let body: ReactNode
    if (loading) body = <SkeletonList rows={2} />
    else if (server) body = <ServerRow server={server} onRemove={() => setConfirmRemove(true)} />
    else body = <Pairing onConnected={() => void refresh()} />

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="flex flex-col sm:max-h-[85dvh] sm:max-w-lg sm:overflow-hidden">
                <DialogHeader>
                    <DialogTitle>Servers</DialogTitle>
                    <p className="text-sm text-muted-foreground">The machine your coworkers run on. One per workspace.</p>
                </DialogHeader>
                <ScrollFade className="-mx-1 min-h-0 flex-1 px-1 py-1">
                    <div className="space-y-4">{body}</div>
                </ScrollFade>
                <ConfirmDialog
                    open={confirmRemove}
                    onOpenChange={setConfirmRemove}
                    title="Remove this server?"
                    description="Your coworkers stop answering until a server is attached again. Everything they know stays on the machine: attach it again to get them back."
                    confirmLabel="Remove"
                    pending={removing}
                    onConfirm={event => {
                        event.preventDefault()
                        void remove()
                    }}
                />
            </DialogContent>
        </Dialog>
    )
}
