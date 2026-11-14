// @vitest-environment happy-dom
import { act, createElement } from 'react'
import { createRoot, type Root } from 'react-dom/client'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { TileLinks, type Tile, type TileLink } from '@rerun/ui/iso-grid'

// The board's link layer: a cable must still draw as one thin path with its comet, and the trace and
// belt variants the factory added must draw their own parts without touching the cable's.

const tile = (id: string, col: number, row: number): Tile => ({ id, position: { col, row }, span: 2, style: { color: '#fff' } })
const TILES = [tile('a', 1, 1), tile('b', 7, 1), tile('c', 1, 7), tile('d', 7, 7)]

let host: HTMLDivElement
let root: Root

beforeEach(() => {
    host = document.createElement('div')
    document.body.appendChild(host)
    root = createRoot(host)
})
afterEach(() => {
    act(() => root.unmount())
    host.remove()
})

function draw(links: TileLink[], tiles: Tile[] = TILES) {
    act(() => root.render(createElement(TileLinks, { tiles, liveLinks: links, containers: [], worldOffset: { left: 0, top: 0 }, svgHalfW: 500, svgHalfH: 500 })))
    return host
}

describe('TileLinks', () => {
    it('draws a cable as one thin path with one comet, and nothing of a trace or a belt', () => {
        const el = draw([{ source: 'a', target: 'b', variant: 'cable' }])
        const paths = el.querySelectorAll('svg path')
        expect(paths).toHaveLength(1)
        expect(paths[0].getAttribute('stroke-width')).toBe('1')
        expect(el.querySelectorAll('.iso-cable-comet')).toHaveLength(1)
        expect(el.querySelectorAll('.iso-trace-trail, .iso-trace-head, .iso-belt-slats')).toHaveLength(0)
    })

    it('draws a trace as its quiet line, three fading trail strokes and one head', () => {
        const el = draw([{ source: 'a', target: 'c', variant: 'trace', color: '#4ade80' }])
        const trails = [...el.querySelectorAll('.iso-trace-trail')]
        expect(trails).toHaveLength(3)
        // The fade lives on stroke-opacity: the rest animation owns `opacity`.
        const fades = trails.map(t => Number(t.getAttribute('stroke-opacity')))
        expect(fades[0]).toBeGreaterThan(fades[1])
        expect(fades[1]).toBeGreaterThan(fades[2])
        expect(el.querySelectorAll('.iso-trace-head')).toHaveLength(1)
        expect(el.querySelectorAll('.iso-cable-comet, .iso-belt-slats')).toHaveLength(0)
    })

    it('draws a belt as edge, band and running slats under the same trace', () => {
        const el = draw([{ source: 'a', target: 'd', variant: 'belt', color: '#f5a524' }])
        expect(el.querySelectorAll('.iso-belt-slats')).toHaveLength(1)
        expect(el.querySelectorAll('.iso-trace-trail')).toHaveLength(3)
        expect(el.querySelectorAll('.iso-trace-head')).toHaveLength(1)
        expect(el.querySelector('.iso-trace-head')?.getAttribute('style')).toContain('#f5a524')
    })

    it('dims the head through a wrapper when an end of its line is dimmed', () => {
        draw([{ source: 'a', target: 'b', variant: 'trace' }], [{ ...TILES[0], dimmed: true }, TILES[1]])
        const head = host.querySelector('.iso-trace-head') as HTMLElement
        expect(head.style.opacity).toBe('')
        expect((head.parentElement as HTMLElement).style.opacity).not.toBe('')
    })
})
