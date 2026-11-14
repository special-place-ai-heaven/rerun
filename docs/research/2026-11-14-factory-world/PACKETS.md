# Packets on lines: wafers that ride, queue and hand off

As of 2026-11-14. This is research only, and nothing here is wired into the app. Target: the floor links of the iso board
(`packages/ui/src/iso-grid/components/TileLinks.tsx`, keyframes in `styles.css`). Small glass wafers (~30 px)
ride the cable polylines between coworkers, queue at a coworker and are handed on. Dark theme.
Allowed: CSS keyframes and transitions, SVG, `offset-path` / `offset-distance`, the app's `motion` ^12.43
(`packages/ui/package.json:63`). No new dependency.
The object follows the brief, a ~30 px glass puck on the floor lines. SPEC.md section 1 has a pod hanging from an
overhead rail instead, and the working tree's new belt comment says spheres. Settle that before building.

This file builds on the sibling notes and does not repeat them: OPEN-SOURCE.md A.1-A.5 (upright parcel on `offset-path`,
one id per job, the `calc(100% - ...)` queue, belt speed, glow without a filter) and MOTION.md R7/R8 (one-shot
handoff comet, three followers). It covers how those look best and what they cost.

## How to read this

- **Provenance** is marked on every snippet: *verbatim* (copied from the named source, whose licence allows it), *adapted* (the
  source's idea and values, re-shaped for the route), or *own* (written here, because no source online did it).
- **Probed** means the doc's exact CSS ran in headless Chrome 157 on this PC: a scratch page with an L-shaped 2:1 iso
  route, positions and computed styles read back over the DevTools protocol, and screenshots. The first probe ran
  looser code and hid two bugs, both now fixed and called out below. Everything else is read from code
  only. The ranking is judged from code and those three frames. I did not watch the pens run.
- **Licence**: public CodePen pens are MIT. Codrops demos are MIT ("Our downloadable demos are licensed under
  the MIT license", tympanus.net/codrops/licensing). Tailwind, Open Props, Magic UI and Motion Primitives are MIT
  (repo LICENSE files).

## What the code already does (read from source, not docs)

**Line numbers are for HEAD `9d223a3`.** While this was being written, the working tree gained uncommitted
`trace` and `belt` link variants (`TileLinks.tsx`, `styles.css`, `types.ts`). The `trace` trail (`TRACE_TRAIL`:
three stacked strokes, `iso-trace-run` on `stroke-dashoffset`) is technique 1 below in a looping form, and its head
already rides the plain route with `offset-rotate: 0deg`. Two cost points apply to it. The trail and the belt slats
(`iso-belt-run`, 13 px strokes) repaint every frame on every such link, all the time, so watch this once there
are many links. The head's `box-shadow` is static, so it is painted once and only the layer moves, which is fine.

- Route: `routeLink` (`TileLinks.tsx:76`) returns 2-4 axis-aligned points. On screen every leg is a 2:1 iso
  diagonal. `Route.length` (`:218`) is the plain polyline length.
- Comet: `cometPath(points, overshoot)` (`:163`) extends the route **into both tiles** and rounds each corner
  with a 5 px `Q`, so its length is not `Route.length`. The comet is a gradient bar with `offset-rotate: auto`,
  `offset-anchor: 100% 50%` and `will-change: transform` (`styles.css:455-478`).
- Per-route timing comes from inline `linear()` easings on shared keyframes (`TileLinks.tsx:347`). That is
  the house way to vary timing per route, and the corner squash below reuses it.
- Pause and reduced motion reach **CSS animations only**: `[data-iso-paused] * { animation-play-state: paused
  !important }` (`styles.css:407-411`), and the reduced-motion block (`:827-852`). The comment at `:384-386`
  rejects SMIL for that reason.

## Doc/code gap found on the way

`TileLinks.tsx:314-316` says `offset-distance` "se résout en transform et se compose sur le GPU". Chromium's own
list of compositor-animatable properties is `backdrop-filter, filter, opacity, rotate, scale, transform,
translate`, plus the paint-worklet pair `background-color, clip-path`
(`third_party/blink/renderer/core/animation/compositor_animations.cc`, `kCompositableProperties`, main branch
read today). It has no `offset-*` entry, so in Chrome the main thread advances an `offset-distance` animation on
every frame. With `will-change: transform` the element is its own layer, so it probably updates a transform without
repainting. Even so, a busy main thread will make it stutter, and a `transform` animation would not. Firefox is said to
run motion path on its compositor (a Bugzilla snippet, not read in full). Settling experiment: a DevTools
Performance trace of the current comet with 4x CPU slowdown, looking for "Animation" on the main thread
and for missed frames. Not fixed here, because this task edits no other file.

What this means for every `offset-path` technique below: the cost is "cheap, on the main thread, no repaint" and never
"GPU-only". Where that matters (dozens of wafers), technique 2 has a pure-`transform` variant that runs on the
compositor. A polyline is straight between its corners, so that variant needs no path at all.

## Surfaces reached

| Surface | Result |
|---|---|
| CodePen | Partly. `codepen.io/.../pen/x.css` returns 403 or a bot check to crawl4ai and to this PC. `cdpn.io/<user>/fullpage/<id>` returns the pen in `srcdoc` (MOTION.md found this route). Read: danwilson ALLbXx, ainalem eYmGLyp, ajv QwwewRM, ycw vYjmMyJ, cssgrid rNQVJWM. trakout OJxREoo is the same "Liquid loader" as ainalem's. Mamboleoo ZELqMOg has no CSS motion (script-driven). danwilson KXoNje has its animation commented out. |
| GitHub | Reached: Magic UI `animated-beam.tsx`, Motion Primitives `border-trail.tsx`, Tailwind `theme.css`, Open Props `props.easing.js` / `props.animations.js`, Chromium `compositor_animations.cc`. |
| Codrops | Reached from this PC (crawl4ai got 502): "Building an Infinite Marquee Along an SVG Path with React & Motion" (2025-06-17), code blocks read. |
| 21st.dev | Metadata only, because component source needs an API key. Aceternity Tracing Beam and Light Runner Path (WebGL) were **seen, code not read**. Licence conflict: 21st.dev lists Tracing Beam as "mit", while ui.aceternity.com/licence is a restrictive Pro licence. Treat it as unclear. |
| React Flow docs | Prose read (animating edges: `<animateMotion>` for SVG, `offsetPath` + WAAPI for nodes). The example code is in an embed and was **not read**. |
| ECG Ribbon (stevetom.vercel.app/lab) | Prose read: 70 `<use>` slices of one path, each a dash window, with tapered width. Code not read. |
| Reddit, X, gists, Dev.to | Nothing usable: only search summaries came back, and no post or gist could be confirmed. No posts by jh3y, Shadeed or Argyle on this subject turned up, so Argyle's Open Props easings are used instead. |
| crawl4ai | The MCP tool failed ("Could not find session"). The REST API worked, with the token read from the environment. |

## Two gotchas the probe caught

- **A CSS `animation-timing-function` applies to each keyframe interval, not to the whole run.** The house trick at
  `TileLinks.tsx:347` works because its keyframes have only `from`/`to`. A per-route `linear()` on a keyframe list with
  a middle stop is applied once per half. The first squash probe peaked a quarter of the way along the route for that
  reason. Any keyframes that carry a per-route `linear()` must have exactly two stops.
- **Do not put `scale` (or `translate`/`rotate`) on the element that rides `offset-path`.** The individual transforms
  are applied outside the offset, so scaling it pulls the element towards the layer's origin and off the line. Echoes
  sized with `scale: .52` sat 100 px off the route. Size them with `width`/`height`, or scale a child. The wafer's
  squash is on its child for this reason.

## Ranked techniques (by how refined they look)

### 1. Tapered comet: stacked dash slices that bend around corners, with a baked glowing head
- **Sources:** ECG Ribbon, https://stevetom.vercel.app/lab/ecg-ribbon (slices of one path, width falling off behind
  the head; prose only). Magic UI Animated Beam's stops, transparent to colour to transparent
  (https://github.com/magicuidesign/magicui/blob/main/apps/www/registry/magicui/animated-beam.tsx, lines 179-186, MIT).
  For a stretch, ajv's "Infinity spinner", https://codepen.io/ajv/pen/QwwewRM (MIT). Its keyframes, verbatim:
  `0% { stroke-dasharray: 0, 158; stroke-dashoffset: 0 } 50% { stroke-dasharray: 79, 158; stroke-dashoffset: -30px }
  100% { stroke-dasharray: 0, 158; stroke-dashoffset: -158px }`: the dash grows mid-flight and shrinks on arrival.
  The snippet below is *own* and **probed**.
- **Look:** a pinpoint head with a soft halo and a tail that thins and fades over ~90 px. The tail **follows the cable
  around the elbow**, appearing on both legs at once in the corner frame. The current comet is a straight bar that pivots
  at a corner, whereas this one bends. The working tree's uncommitted `trace` variant (see the note above) already
  loops this effect.
- **Core:**
  ```css
  .pk-slice { fill: none; stroke: #4ade80; stroke-linecap: round; stroke-linejoin: round;
    stroke-dasharray: var(--L) 4000px;                       /* one dash of length L */
    animation: pk-slice var(--d) cubic-bezier(.45,0,.2,1) forwards, pk-fade var(--d) linear forwards; }
  @keyframes pk-slice { from { stroke-dashoffset: var(--L) }                       /* hidden before the start */
                        to   { stroke-dashoffset: calc(var(--L) - var(--len)) } }  /* head at the end */
  @keyframes pk-fade { 85% { opacity: 1 } to { opacity: 0 } }                      /* the tail leaves, no cut */
  .pk-head { position: absolute; top: 0; left: 0; width: 14px; height: 14px; border-radius: 50%;
    background: radial-gradient(circle, #f0fdf4 0 18%, rgb(74 222 128 / .55) 35%, transparent 70%);
    offset-path: var(--route); offset-rotate: 0deg;          /* no top/left offset: the anchor centres it */
    animation: pk-run var(--d) cubic-bezier(.45,0,.2,1) forwards, pk-fade var(--d) linear forwards; }
  @keyframes pk-run { from { offset-distance: 0% } to { offset-distance: 100% } }
  ```
  ```tsx
  const SLICES = [[90, 1, 0.12], [55, 1.5, 0.25], [28, 2, 0.5], [10, 2.5, 0.95]] // tail px, width, opacity
  // In the SVG: the same d, duration and easing, so every slice has its head at the same point.
  <g style={{ ['--d' as string]: '900ms', ['--len' as string]: `${length}px` }}>
      {SLICES.map(([L, w, o]) => <path key={L} className="pk-slice" d={d} strokeWidth={w} strokeOpacity={o}
          style={{ ['--L' as string]: `${L}px` }} />)}
  </g>
  // In the HTML layer: the head, and the end of the one-shot (the probe saw it fire and the comet go).
  <div className="pk-head" style={{ ['--route' as string]: `path("${d}")`, ['--d' as string]: '900ms' }}
       onAnimationEnd={e => e.animationName === 'pk-run' && onCometDone(id)} />
  ```
  Use `strokeOpacity` for each slice's level, because `pk-fade` animates `opacity` and would override it.
- **Cost:** `stroke-dashoffset` cannot run on the compositor, so 4 short strokes repaint every frame while it runs.
  That is fine for one-shots, which are limited to the handoffs in progress (MOTION.md R7). It is wrong as a loop on
  every cable. The head moves with `offset-distance` (main thread, no repaint), with its glow baked into a gradient.
- **Route fit:** the plain route `d` (`Route.d`, `TileLinks.tsx:218`), not `cometPath`. The slices bend because they
  are the stroke, and `--len` must be the length of the same path.

### 2. The wafer: an upright glass disc that squashes as it turns each corner
- **Sources:** Motion's motion-path example, https://motion.dev/examples/react-motion-path (`offsetDistance` animated
  together with `scale`), and the house per-route `linear()` (`TileLinks.tsx:347`). The snippet is *own* and **probed**:
  mid-leg the disc reads `scale: 1`, and at the elbow (x 209 of 210) it reads `scale: 1.18 0.82`.
- **Look:** a flat iridescent disc, a 2:1 ellipse so it lies on the floor. It stays upright as it glides and gives a
  small, weighty squash (wider and flatter) at each elbow. Its travel is technique 3's transition, so one element covers
  both the ride and the queue.
- **Core:**
  ```css
  .pk-disc { width: 100%; height: 100%; border-radius: 50%; opacity: .9;
    background: radial-gradient(ellipse at 35% 30%, rgb(255 255 255 / .7), transparent 40%),
                conic-gradient(from 200deg, #67e8f9, #a78bfa, #f0abfc, #67e8f9);
    box-shadow: 0 0 0 1px rgb(255 255 255 / .35) inset, 0 3px 0 -1px rgb(15 23 42 / .9); } /* static: painted once */
  .pk-wafer.arriving .pk-disc { animation: pk-squash var(--d) var(--squash-ease) both; }
  @keyframes pk-squash { from { scale: 1 1 } to { scale: 1.2 .8 } }   /* two stops only: see the gotcha */
  ```
  ```ts
  // Travel easing as [time, progress] stops. The same stops are the arrival transition's linear().
  const TRAVEL: [number, number][] = [[0, 0], [0.2, 0.1], [0.8, 0.9], [1, 1]]
  const travelEase = `linear(${TRAVEL.map(([t, p]) => `${p} ${t * 100}%`).join(', ')})`
  function timeAt(p: number) {
      const i = Math.max(1, TRAVEL.findIndex(([, q]) => q >= p))   // first stop at or past p
      const [[t0, p0], [t1, p1]] = [TRAVEL[i - 1], TRAVEL[i]]
      return t0 + ((p - p0) / (p1 - p0)) * (t1 - t0)
  }
  // A 0 -> 1 -> 0 bump at the moment the wafer passes each corner on its way to the slot at `end` px.
  // shortcut: +-5% windows overlap when corners are under ~10% of the ride apart; clamp if routes get that short.
  function squashEase(points: ScreenPoint[], end: number, w = 5) {
      const stops = ['0 0%']
      let run = 0
      for (let i = 1; i < points.length - 1; i++) {
          run += distance(points[i - 1], points[i])
          if (run >= end) break
          const t = +(timeAt(run / end) * 100).toFixed(1)
          stops.push(`0 ${t - w}%`, `1 ${t}%`, `0 ${t + w}%`)
      }
      return `linear(${stops.join(', ')}, 0 100%)`
  }
  ```
- **Cost:** `offset-distance` on the main thread, plus a `scale` that runs on the compositor. There is no
  `backdrop-filter`: the glass is gradients and an inset ring, so nothing samples the board behind it per frame.
- **Composited variant (own, not probed):** a polyline is straight between its vertices, so the same ride can be a
  `transform` keyframe list with one stop per vertex at `offset = cumulativeLength / total`, with the travel easing on
  the whole effect, run by WAAPI or `motion`'s `animate()`. `transform` is on Chromium's compositor list. But a WAAPI
  or `motion` animation is not reached by `[data-iso-paused]`, which only sets `animation-play-state` for CSS
  animations, so it has to be paused by hand from the board's `paused` prop. It is worth this only with dozens of wafers.
- **Route fit:** `offset-rotate: 0deg` keeps the disc upright on both legs. A tail on the wafer must be a **sibling**
  on the same path and timing with `offset-rotate: auto`, not a child, because a child rides the parent's unrotated
  box. Do not add `top/left` offsets on top of `offset-anchor`: in the first probe the wafers were centred twice and
  every one sat 15 px back.

### 3. Queue backing up with minimum spacing, closing up in a ripple
- **Sources:** OPEN-SOURCE.md A.3 (`calc(100% - (i + 1) * gap)` with a transition). The Codrops marquee,
  https://tympanus.net/codrops/2025/06/17/building-an-infinite-marquee-along-an-svg-path-with-react-motion/ (MIT): one
  shared value, items spaced by index, and `zIndex` from progress so later items paint over earlier ones. Open Props
  `--ease-spring-3`, https://github.com/argyleink/open-props/blob/main/src/props.easing.js (verbatim, MIT). For a convoy
  that moves as a block, cssgrid's https://codepen.io/cssgrid/pen/rNQVJWM (MIT): static `offset-distance: 5%, 10%...`
  per item plus one shared `move` keyframes with `animation-composition: accumulate`, so the run adds to each item's
  spacing. No source covered **backing up**, so the hold-and-ripple is *own*. It is **probed**.
- **Look:** wafers stand one gap apart on the incoming cable, nearest the coworker first. When the head is taken, the
  rest step up from the front one after another (70 ms stagger, like traffic moving off a light) with a small spring
  overshoot. A new wafer rides in from the source, squashing at the corners, and stops at the tail.
- **Core:**
  ```css
  .pk-wafer { position: absolute; top: 0; left: 0; width: 30px; height: 15px;
    offset-path: var(--route); offset-rotate: 0deg; offset-anchor: 50% 50%;
    offset-distance: calc(100% - 18px - var(--i) * 34px);            /* slot i, px from the arrival end */
    transition: offset-distance 560ms var(--spring) calc(var(--i) * 70ms); }  /* --spring: Open Props spring-3 */
  @starting-style { .pk-wafer { offset-distance: 0% } }              /* a freshly mounted wafer starts at the source */
  .pk-wafer.arriving { transition: offset-distance var(--d) var(--travel-ease); }  /* the ride itself */
  ```
  ```tsx
  // One element per wafer per link: the key changes on each handoff, so @starting-style runs again from 0%.
  <div key={`${jobId}:${link.id}`} className={arriving ? 'pk-wafer arriving' : 'pk-wafer'}
       style={{ ['--route' as string]: `path("${d}")`, ['--i' as string]: slot, ['--d' as string]: `${rideMs}ms`,
                ['--travel-ease' as string]: travelEase, ['--squash-ease' as string]: squashEase(points, length - 18 - slot * 34) }}
       onTransitionEnd={() => setArriving(false)}>
      <div className="pk-disc" />
  </div>
  ```
- **How 2 and 3 join:** a wafer never runs a travel animation. It is mounted on the link to its next coworker with
  `arriving`, rides by transition to its slot (slot 0 when the queue is empty, which is the face itself), squashes at
  the corners it passes before that slot, then drops `arriving` and from then on only closes up. On handoff the
  receiver's head is unmounted and a new wafer is mounted on the next link, starting at 0%, which is the face it left.
  `@starting-style` needs Chrome/Edge 117, Firefox 129 or Safari 17.5 (MDN browser-compat-data). Before that, the
  wafer appears in its slot with no ride, which is an acceptable floor.
- **Probe readings** (legs of 178.9 px): three parked wafers and a fourth that rode in settled 18, 52.6, 86.4 and 120 px
  from the end. After the head was removed, the rest closed up to 18, 52.6 and 86.4. `calc(% - px)` interpolates, and a
  mid-transition computed value was `calc(98.591% - 17.7464px)`.
- **Spacing rule from the probe:** on a 2:1 iso leg a wafer moves 0.894 px across the screen per px of path. Wafers of
  screen width W therefore need a path gap of at least W / 0.894, which is 34 px for 30 px wafers. If `n * gap` would run
  past the corner, cap the gap at `legLength / (n + 1)` and show `+k` on the last wafer instead of queueing round the elbow.
- **Cost:** transitions of `offset-distance` run on the main thread, and only while the line moves.
  `animation-play-state` does **not** pause transitions, so `[data-iso-paused]` does not freeze a close-up in progress.
  The close-up just finishes, which is acceptable for a change of state. Under reduced motion, use `transition: none`.
- **Route fit:** slots count from the arrival end, so the queue needs the **plain route**. On `cometPath` the 100% end
  lies inside the target tile (the overshoot), and slot 0 would be hidden under the block. OPEN-SOURCE.md A.1 mentions
  `cometPath` only as what that layer already builds and leaves the parcel's own path unstated. It should be the plain route.

### 4. Trailing particles: echoes that stretch with speed, or a wake of lights
- **Sources:** ycw's "smooth", https://codepen.io/ycw/pen/vYjmMyJ (MIT): 64 copies of one SVG `<g>` on the same
  `offset-path` (`animation: 4s f infinite ease-in-out`), each delayed by ~2.3 ms more than the last, so the copies
  spread out where the motion is fast and bunch up where it is slow. danwilson, https://codepen.io/danwilson/pen/ALLbXx
  (MIT): static dots at fixed `offset-distance` steps, all with one `pulse` keyframes and staggered delays. *Adapted*;
  the echoes are **probed** with an animation to 100% (all five measured 0.0 px off the route); the transition form
  below uses the same mechanism and was not run.
- **Look:** echoes give a short trail of fading copies behind the wafer that stretches on the straight and gathers at
  the corners and the stop: speed is visible without a blur. The wake is the reverse: dots that sit on the cable flare
  as the wafer passes and die out behind it.
- **Core:**
  ```css
  .pk-echo { position: absolute; top: 0; left: 0; width: 10px; height: 10px; border-radius: 50%;  /* size, not scale */
    background: #a78bfa; offset-path: var(--route); offset-rotate: 0deg;
    offset-distance: var(--slot);                       /* the same slot distance as its wafer */
    transition: offset-distance var(--d) var(--travel-ease) var(--lag); }
  @starting-style { .pk-echo { offset-distance: 0% } }
  /* danwilson, verbatim: */
  .dot { width: .4rem; height: .4rem; background: #f5f5fb; border-radius: 50%; opacity: 0;
    animation: pulse 3200ms infinite ease-in-out; }
  .dot:nth-of-type(1) { offset-distance: 10%; animation-delay: 320ms; }     /* ... one rule per 10% */
  @keyframes pulse { 20% { opacity: 1; } 40% { opacity: 0; } }
  ```
  ```tsx
  // Mounted with an arriving wafer, unmounted on their own transitionend.
  {[1, 2, 3, 4].map(k => <div key={k} className="pk-echo"
      style={{ ['--lag' as string]: `${k * 14}ms`, opacity: 0.6 - k * 0.11 }} />)}
  ```
  For the wake, make `pulse` one-shot, put dots every ~16 px of the route, and set each dot's delay to
  `timeAt(dotDistance / end) * rideMs` (technique 2), so it flares exactly when the wafer is over it.
- **Cost:** echoes are N more main-thread `offset-distance` elements per wafer, so keep N at 3-5. Wake dots never move
  and only animate `opacity`, which runs on the compositor, but that is ~20 elements per 350 px route (not measured),
  so mount them only while a wafer rides that link.
- **Route fit:** both follow the plain route through the corners with nothing extra. The echoes reuse the wafer's
  `--route`, `--slot`, `--d` and `--travel-ease` (set them on a shared parent), so they arrive just behind it and
  then vanish under it.

### 5. Arrival ping: a floor ring at the receiving face
- **Sources:** the house `agent-ping` (`styles.css:139-143`: opacity 0.6 to 0 and `scale(1)` to `scale(1.6)` by 70%), used
  on tiles as two rings 0.6 s apart (`TileBlock.tsx:373`, `:386`). Tailwind's `ping`,
  https://github.com/tailwindlabs/tailwindcss/blob/main/packages/tailwindcss/theme.css (MIT), is the same idea (`75%, 100%
  { transform: scale(2); opacity: 0 }`). Reuse the house keyframes rather than adding Tailwind's. *Adapted*, not probed.
- **Look:** one thin ring, drawn as a 2:1 ellipse so it lies on the floor, swells and fades at the face the wafer just
  reached. Pair it with the receiver's one-shot shudder (OPEN-SOURCE.md A.2) so the coworker visibly catches it.
- **Core:**
  ```css
  .pk-ping { position: absolute; width: 24px; height: 12px; margin: -6px 0 0 -12px; border-radius: 50%;
    border: 1.5px solid rgb(74 222 128 / .8); animation: agent-ping 900ms cubic-bezier(0, 0, .2, 1) both; }
  ```
  Placed at `points[points.length - 1]` (the face centre) and mounted on the wafer's `transitionend`. It is
  positioned with `left/top`, not `offset-path`, so `transform: scale` is safe here.
- **Cost:** `transform` + `opacity`, both on the compositor.

### 6. The head lights the cable from inside (a blob seen through a mask of the line)
- **Source:** Motion Primitives Border Trail,
  https://github.com/ibelick/motion-primitives/blob/main/components/core/border-trail.tsx (MIT, last pushed 2026-09-28).
  A blob rides `offsetPath: rect(0 auto auto 0 round ${size}px)` with `animate={{ offsetDistance: ['0%', '100%'] }}`
  inside a layer whose `mask-composite: intersect` keeps only the border ring. *Adapted* to a cable mask and **probed**:
  the screenshot shows only a short lit stretch of the line itself, with no light off the line.
- **Look:** instead of a dot passing over the line, a soft light travels **inside** the cable, so only the cable's own
  stroke glows where it passes. It is very clean on a dark floor.
- **Core:**
  ```css
  .pk-glowline { position: absolute; inset: 0; mask: var(--cable-mask) no-repeat 0 0 / 100% 100%; }
  .pk-blob { position: absolute; top: 0; left: 0; width: 48px; height: 48px; border-radius: 50%;
    background: radial-gradient(circle, #f0fdf4, rgb(74 222 128 / .7) 30%, transparent 70%);
    offset-path: var(--route); offset-rotate: 0deg; animation: pk-run var(--d) cubic-bezier(.45,0,.2,1) forwards; }
  ```
  ```ts
  // The cable's own stroke as the mask, the same size as the layer (svgHalfW * 2 by svgHalfH * 2).
  const svg = `<svg xmlns='http://www.w3.org/2000/svg' width='${w}' height='${h}'><path d='${d}' stroke='#000'
    stroke-width='3' stroke-linecap='round' stroke-linejoin='round' fill='none'/></svg>`
  const cableMask = `url("data:image/svg+xml,${encodeURIComponent(svg)}")`
  ```
- **Cost:** not measured. The mask is static, but the layer under it changes every frame. Probe the frame time before
  using it on more than a few cables. Border Trail drives the blob from `motion`, which `[data-iso-paused]` does not
  reach; the CSS animation above does not have that problem.
- **Route fit:** good. The light bends at corners because the mask is the cable.

### 7. Dash-march synchronised to the wafers
- **Source:** the app's own `iso-link-current` (`styles.css:392-403`, dash `6 16`, period 22, 1.2 s), and OPEN-SOURCE.md
  A.4 (one belt speed for dashes and parcels). *Own* sync, not probed.
- **Look:** marching dashes on occupied cables at exactly the wafers' speed, so the line and its cargo read as one belt.
  On its own this is the most ordinary technique here. Its value is the sync, and stopping the dashes on a hold.
- **Core:**
  ```ts
  // The current advances DASH_PERIOD px per 1.2 s; give the ride the same speed.
  const rideMs = Math.round((length / DASH_PERIOD) * 1200)
  ```
  ```css
  [data-held] .iso-link-current { animation-play-state: paused; }   /* a hold stops the belt and its queue */
  ```
- **Cost:** a `stroke-dashoffset` repaint per frame per cable, so run it only on cables that carry something.

### 8. Gradient sweep (Magic UI Animated Beam): rejected for these routes
- **Source:** https://github.com/magicuidesign/magicui/blob/main/apps/www/registry/magicui/animated-beam.tsx (MIT). A
  `motion.linearGradient` with `gradientUnits="userSpaceOnUse"` animates `x1: ["10%", "110%"], x2: ["0%", "100%"]`, with
  `y1`/`y2` fixed at `0%` and `ease: [0.16, 1, 0.3, 1]`.
- **Why rejected:** the light moves along the **screen x axis**, not along the path. On an iso L both legs share x
  ranges, so the light shows on both legs at once and never turns the corner. It also repaints the stroke every frame
  and runs from `motion`, outside the pause cascade. Its stop recipe is reused in technique 1.

### 9. Gooey merge (ainalem "Liquid loader"): rejected for cost
- **Source:** https://codepen.io/ainalem/pen/eYmGLyp (MIT; trakout OJxREoo is the same pen). It applies
  `feGaussianBlur stdDeviation="7"`, then `feColorMatrix values="... 0 0 0 20 -10"`, then `feComposite operator="atop"`
  to strokes with marching dashes, so blobs melt together where they touch.
- **Why rejected:** a filter over the whole layer runs again on every frame in which anything inside it moves. Queued
  wafers merging like liquid would look striking, but this is the per-frame filter work `styles.css` warns against.

Also seen but not ranked: React Flow `<animateMotion>` edges (https://reactflow.dev/examples/edges/animating-edges),
which use SMIL and so do not obey the pause cascade. The Codrops marquee's rAF loop (`useAnimationFrame` moving a
motion value) has the same pause problem; its index spacing and `zIndex` from progress are taken into technique 3.

## Verdict

Build in this order: **2 + 3** (the wafer and its queue are one element), **1** (a comet for each real handoff), then
**5** (arrival ping, house keyframes) and **4** (echoes) as polish. All of them are CSS animations or transitions, so
they keep the pause and reduced-motion cascade, and all of them ride the **plain route** (`Route.d` / `Route.length`),
never `cometPath`. Under reduced motion: no comet, echoes, wake or ping, and wafers appear in their slot (`transition: none`).

Confidence: medium-high on look and correctness. Techniques 1-4 and 6 ran in Chrome 157 with the CSS written here, and
the squash and queue were read back as numbers. Medium on cost at scale, because the main-thread `offset-distance`
finding comes from Chromium source, not from a trace. What would raise it: the DevTools trace named in the gap section,
run with 20 wafers moving at once, and the composited `transform` variant of technique 2 measured against it.
