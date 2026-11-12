import { describe, expect, it } from 'vitest'
import { barConfig, DOCK_APPS, dockConfig, openboxConfig } from './panels.js'

describe('desktop panels', () => {
    it('gives the dock one item per app, with its icon, its open state and the call that opens it', () => {
        const config = dockConfig('/opt/rerun/apps/engine/assets/desktop/icons')
        expect(config).toContain('panel_items = EEE')
        expect(config).toContain('panel_position = bottom center horizontal')
        for (const { app, label, windowClass } of DOCK_APPS) {
            expect(config).toContain(`execp_tooltip = ${label}`)
            expect(config).toContain(
                `xdotool search --onlyvisible --class '${windowClass}' >/dev/null 2>&1 && echo '/opt/rerun/apps/engine/assets/desktop/icons/${app}-open.png' || echo '/opt/rerun/apps/engine/assets/desktop/icons/${app}.png'`,
            )
            expect(config).toContain(`-d '{"app":"${app}"}' "$RERUN_DESKTOP_ENGINE/agents/$RERUN_DESKTOP_AGENT/desktop/apps"`)
        }
    })

    it('reads the session token and the agent from the environment, never the engine key or the file', () => {
        process.env.RERUN_API_KEY = 'secret-key'
        const config = dockConfig('/icons') + barConfig()
        expect(config).not.toContain('secret-key')
        expect(config).toContain('Bearer $RERUN_DESKTOP_TOKEN')
        expect(config).not.toContain('RERUN_API_KEY')
        expect(barConfig()).toContain(`printf '%s' "$RERUN_DESKTOP_AGENT_NAME"`)
        delete process.env.RERUN_API_KEY
    })

    it('shows the name on the left and the time on the right of the top bar', () => {
        const config = barConfig()
        expect(config).toContain('panel_items = EFC')
        expect(config).toContain('panel_position = top center horizontal')
        expect(config).toContain('time1_format = %H:%M')
    })

    it('keeps the window manager without key bindings and without a way to minimise', () => {
        const config = openboxConfig()
        expect(config).toContain('<keyboard></keyboard>')
        expect(config).toContain('<name>Rerun</name>')
        expect(config).toContain('<titleLayout>LMC</titleLayout>')
    })
})
