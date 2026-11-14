# Inspiration: an animated factory world for the coworkers
as_of 2026-11-14. Status: DRAFT, research only. No code was changed.

Companion to `docs/research/2026-11-14-factory-view/DESIGN.md` (the flat line and floor mocks, which the owner
called "a receipt"). This file collects references and techniques for an isometric, moving version in the
app's own style (`packages/ui/src/iso-grid`).

## How this was gathered, and what it is worth

- **Evidence tier** is given for every reference: **source read** (files fetched from the repository and read),
  **metadata** (licence, stars and last push from the GitHub API, README only), or **lead** (named by search or a
  third-party page, never opened at the source).
- **No motion was watched.** Every description of motion below comes from reading code or a README, not from
  running the project or watching a video. Treat timings as what the code says, not as how it feels.
- **Tools:** the crawl4ai MCP returned "Could not find session" (HTTP 404) on every call, so pages were read with
  WebFetch and repositories with the GitHub API and raw files over curl. Codrops and CodePen refused WebFetch
  (HTTP 403); those items stay leads.
- **Community surfaces:** Hacker News gave real signal (below). Searches aimed at X, Reddit and Dribbble returned
  only aggregator pages, stock-animation shops and mirrors; no primary source came from them, so none is cited
  as evidence.
- **Licences:** an MIT code licence does not cover the art. Pixel Agents credits a third-party character pack
  and Munder Difflin ships tilesets with their own attribution file. Borrow techniques, never sprites or
  tiles. shapez.io is GPL-3.0 and pixel-agent-desk has no clear licence: ideas only, no code.
- Six references were read at the source or as an article (1 to 6); the rest are metadata or leads.
- Worked solo; no teammate agent was consulted.

## What the app already has (the base to reuse)

Read in `packages/ui/src/iso-grid`. Most new motion is a small step from these:

| Already there | Where | Why it matters for the factory |
|---|---|---|
| Axis-aligned cable routes between tiles, elbow or Z shape | `components/TileLinks.tsx` `routeLink` | The road a job travels on between stations. |
| Rounded SVG path from a route, extended into both tiles | `TileLinks.tsx` `cometPath` | Feeds `offset-path` directly; a job can ride it like the comet does. |
| One element moved with `offset-distance` on the GPU | `styles.css` `iso-cable-comet` | Same mechanism moves a crate. |
| Per-link speed, pause and phase from a hash; travel/rest share carried by `linear()` easing | `TileLinks.tsx` `cableTiming` | The pattern for keeping many copies out of step. |
| Squash and stretch by top translate plus wall `scaleY`; `translate`/`scale` kept apart from `transform` so a stretch adds to a running bob | `styles.css` `iso-buddy-bob-*`, `iso-buddy-shudder-*`, `[data-buddy-stretched]` | Landing squash and "receiving" gulp come for free. |
| Floor light pool that dims as the buddy rises; light band sweep; blink; glance | `styles.css` `iso-buddy-pool`, `-sweep`, `-blink`, `-glance` | Station "on" states. |
| A scheduler per agent with weighted next state and random dwell, so agents never move in turn | `hooks/useLivingBoard.ts` `nextStatus`, `dwell` | The idle-behaviour picker. |
| Freeze everything when unseen; reduced-motion cuts | `styles.css` `[data-iso-paused] *` and the two `prefers-reduced-motion` blocks; `IsoGrid.tsx` sets `data-iso-paused` | Every new loop must be a class in `styles.css` to inherit these. |
| Depth order by cell | `iso.ts` `tileZ(col, row, span)` | A moving object must take the z of the cell it is crossing. |
| A first factory world on a sample loop: boxes per room, coworkers as 2x2 buddies, a copy drawn as its coworker see-through, a job as a GitHub tile that drops in beside whoever holds it, a running beam while it works | `apps/ui/components/factory/factory-scene.ts`, `FactoryWorld.tsx` (commits df1da8e, 9d223a3); an untracked lab page `apps/ui/app/render/lab/factory/page.tsx` from another session, not mine and not touched | The baseline the techniques below upgrade: jobs that travel instead of dropping in (T1, T2), copies that bud and dissolve (T4), queues (T7). |
| `motion` v12 and `canvas-confetti` | `packages/ui/package.json`, `apps/ui/lib/confetti.ts` | No new dependency is needed for anything below. |

## Ranked references

Health figures are from the GitHub API on 2026-11-14.

### 1. Munder Difflin - an office of agents on one floor
- https://github.com/HarnessMD/munder-difflin (redirects from chaitanyagiri/munder-difflin). MIT. About 9.5k
  stars, pushed 2026-11-14, active. Electron, React, PixiJS. **Source read.**
- Many agents working at once on one floor. The cast is 15 distinct named characters (`cast.ts`); the
  "clone" of its README is a clone of the user, not several copies of one agent. No reference read shows
  identical copies of one agent; T4 below is composed here, not borrowed.
- Motion in the code:
  - `src/renderer/src/scene/office/MessageEnvelope.ts`: a message flies from sender to receiver on a lifted
    arc (x eased, y minus `ARC_LIFT * sin(pi * t)`), duration from distance (230 px/s, clamped 0.8 to 2.0 s),
    short fade in and out, then a 0.34 s ring burst on arrival. Tint by kind of message (ask cool, answer
    warm, refusal red; escalation to the human its own colour).
  - `DeskScreen.ts`: a desk monitor switches from an off tile to an on tile while its agent sits there, plus
    scrolling lines and a blinking cursor inside the screen area.
  - `ThoughtBubble.ts`, `ToolBubble.ts`: a bubble over the head with "icon + target" (for example `> App.tsx`),
    a five-state fade machine (hidden, fading in, visible, lingering 1.2 s, fading out), a character cap so
    long paths wrap to a few lines.
  - `SeatPool.ts`: each new agent takes the first free seat in a fixed order; release is idempotent.
  - `Camera.ts`: smooth lerp (0.08 per frame) and a short "nudge toward" the selected agent at 40 percent.
- Community: Hacker News item 49398152, 312 points, 145 comments. For: "when there is a lot happening at once,
  it is a mistake to communicate it all with text". Against: "cringe", and "pipelines, not agents; roles,
  not agents". Lesson: every motion must carry a real state, or the scene reads as a toy.
- Several pieces are ported from shahar061/the-office (ISC, 18 stars), credited in the files.

### 2. Pixel Agents - Claude Code sessions as office characters
- https://github.com/pixel-agents-hq/pixel-agents (redirects from pablodelucca/pixel-agents). MIT. About 10.2k
  stars, pushed 2026-11-10, active. Canvas 2D in a VS Code webview or a browser. **Source read.**
- Motion in the code (`webview-ui/src/office/engine/`):
  - `characters.ts`: a state machine TYPE, IDLE, WALK. Active agents find a path to their seat and type; when
    inactive they stand, wander a random number of moves with pauses, then return to rest.
  - `matrixEffect.ts`: spawn and despawn as a column sweep: each column starts at a seeded stagger, a bright
    head row moves down revealing the sprite, a fading trail follows, a hash-based flicker shows about 70
    percent of trail pixels.
  - `blink.ts`: each character has its own blink clock; gaps are a floor plus an exponential wait, capped;
    some blinks come in pairs; characters at work blink less ("focus stretch").
  - `sprites/bubble-waiting.json`, `bubble-permission.json`: distinct bubbles for "waiting" and "needs
    permission".
- Character art is credited to a third-party pack (JIK-A-4, Metro City): not covered by the MIT licence.
- Community: Show HN items 49730005 and 49648023 (under 10 points each); the popularity is on GitHub and the
  VS Code marketplace, not on Hacker News.

### 3. Claude Office Visualizer - boss, employees, elevator, queues
- https://github.com/paulrobello/claude-office. MIT. 616 stars, pushed 2026-11-11, active. Next.js, PixiJS,
  a backend state machine pushed over WebSocket. **Source read.**
- Motion in the code (`frontend/src/`):
  - `systems/queuePositions.ts`: an arrival queue (get work from the boss) and a departure queue (hand work
    in), each with fixed standing slots and one "head" slot at the desk; arrival has priority.
  - `components/game/Elevator.tsx`: doors scale open over 0.5 s; new agents appear inside on a 2 by 3 grid of
    spawn spots.
  - `components/command/ExitingPeer.tsx`: an ended agent walks to the door (first 55 percent), steps in and
    fades. **Only sessions that ended while the view was open play this**; ones ended before are simply gone.
  - `systems/compactionAnimation.ts`: when context is compacted, the boss walks to a trash can and stomps it
    36 times while the context meter falls: a joke tied to a real number.
  - `components/game/city/timeUtils.ts`: night, dawn, day, dusk phases with a progress value, for a window.
  - `components/game/whiteboard/KanbanMode.tsx`: the kanban lives on a whiteboard prop inside the office.

### 4. Vibecraft - one agent walking between tool stations
- https://github.com/Nearcyan/vibecraft. MIT. About 1.5k stars, last push 2026-01-18 (about ten months ago:
  stalled). Three.js. **Source read** (two files plus README).
- Stations by tool (bookshelf for read, workbench for edit, terminal for shell, portal for sub-agents, board
  for to-dos); the agent walks to the station of the tool it uses; floating labels above the active station
  show the file or command; sub-agents spawn as mini copies at the portal.
- `src/entities/animations/WorkingBehaviors.ts`: a different work loop per station: reading (eyes scan left to
  right three lines per cycle with a quick return, occasional page flip), tinkering (hammer arc), writing
  (small arm strokes with a pause to look up), typing (12 cycles, alternating arms).
- `src/entities/animations/IdleBehaviors.ts`: a library of idle acts picked at random: look around, curious
  tilt, happy bounce, stretch, double blink, peek, sleepy nod, several dances.

### 5. AI Town - smooth motion from coarse server updates
- https://github.com/a16z-infra/ai-town. MIT. About 10.8k stars, pushed 2026-11-05, stable. PixiJS on a Convex
  backend. **Source read** (two files).
- `src/hooks/useHistoricalTime.ts`: the client plays the world slightly in the past: it stores the step
  intervals of the server and replays them, so motion between two server steps is interpolated instead of
  jumping. Directly relevant: the factory data refreshes about every 30 seconds (DESIGN.md section 5).
- `src/components/Character.tsx`: flags for thinking and speaking show a small bubble; the sprite animates
  only while moving.

### 6. Jhey Tompkins - CSS 3D printer and package toggle
- https://dev.to/jh3y/printcss-but-not-how-you-know-it-creating-a-3d-css-printer-1o0k and
  https://dev.to/jh3y/how-to-make-a-pure-css-3d-package-toggle-f55. Pure CSS. **Article read**; the CodePen
  demos themselves were not opened. The default CodePen licence for public pens is MIT; confirm on the pen
  before copying code.
- Printer: a sheet is split into three elements (transfer, fly, feed); all timings derive from one custom
  property (`--load-speed`), so the sequence stays in sync; a status light changes hue while printing.
- Package: each flap hinges on its shared edge (`transform-origin: 50% 100%` for a top flap); one 0 to 1
  property (`--packaged`) drives every rotation; a per-element `--step` staggers `transition-delay`, so the
  box folds piece by piece and unfolds in reverse.

### 7. shapez.io - belts as paths (ideas only, GPL-3.0)
- https://github.com/tobspr-games/shapez.io. GPL-3.0: **no code may be copied** into this repository.
  About 7k stars. **Metadata** plus patch notes found by search.
- One idea from its patch notes: items on a belt are kept as spacing along one belt path, not per belt cell,
  which made motion cheaper and smoother. The same notes fixed belts that looked like they ran backwards at
  high speed, blamed on the frame rate of the belt animation.

### 8. CSS-in-DOM 3D engines - heerich and polycss
- https://github.com/meodai/heerich (MIT, 633 stars, pushed 2026-11-07): voxel scenes projected to SVG, no
  dependencies, oblique and perspective cameras. **Metadata.**
- https://github.com/layoutit/polycss (MIT, 772 stars, pushed 2026-08-25): polygon meshes in HTML with
  `matrix3d`. The old name `LayoutitStudio/voxcss` (the Codrops "CSS Meets Voxel Art" article, March 2025)
  now redirects here, but the description changed from stacked voxel grids to polygon meshes, so what it is
  today is unconfirmed. **Metadata.**
- Use: only if a station ever needs a shape the current block-and-wall drawing cannot make. Not needed for
  anything in this file.

### 9. Leads, not read at the source
- Viberia (Product Hunt; Tauri; closed source as far as the page shows): agents on an isometric map grouped in
  "buildings" that run in sequence (spec, then code, then review); its maker compares chaining flows to
  stacking buildings in Factorio. Closest concept to a factory line; nothing to borrow in code.
- pixtuoid (https://github.com/pixtuoid/pixtuoid, MIT, 560 stars, Rust terminal): when a floor fills, a new
  floor opens. A capacity idea.
- Moltcraft, OfficeAI, Agent Office: isometric agent offices named by aggregator pages; no repository read.
- steveeeie conveyor pen (https://codepen.io/steveeeie/pen/VyQXqK) and the Codrops voxel article: both refused
  the fetch (403).
- FactorishJS (https://github.com/msakuta/FactorishJS, MIT, dormant since 2021): browser Factorio clone.
- pixel-agent-desk (now zep-ia/pixel-agent-desk): GitHub reports its licence as NOASSERTION (not a standard
  licence it can recognise); do not borrow until the licence file is read.

## Borrowable techniques

Rules that hold for every item below:
- **CSS keyframe loops are classes in `styles.css`**, so `[data-iso-paused] *` freezes them (it sets only
  `animation-play-state`) and each one is added to a `prefers-reduced-motion` block.
- **Everything else gates in JS**: `motion` `animate` calls (T1 alternative, T2), the move queue of T10, the
  idle timers of T6 and the CSS transitions of T3, T7, T12 and T14 are not touched by that rule or by the CSS
  reduced-motion blocks. They must read the paused flag and `usePrefersReducedMotion`, as `TileBlock.tsx`
  already does for its timers (comment at line 56). Under reduced motion a one-shot move becomes a jump to
  the end with a 150 ms opacity cross-fade.
- **Glow is the opacity of a ready-made layer** (a blurred or gradient element drawn once), never an animated
  `box-shadow` or `filter`: with a dozen copies on screen those repaint every frame.
- **State shows by shape and word, never colour alone** (DESIGN.md section 2). Motion adds to the shape, it
  does not replace it.
- **Depth:** `TileLinks` is mounted under every tile (`IsoGrid.tsx` line 1291), so anything in the links layer
  passes under all blocks. Two options for a crate: (a) under the tiles like the comet, simple, but a crate
  never passes in front of a block; (b) a sibling of the tiles with `zIndex` from `tileZ(col, row, span)` of
  the cell it is crossing, set at the start of each leg of its route (a route from `routeLink` has two to
  four straight legs). (b) is correct in front of blocks and is the one to spike.

### T1. The job crate rides the cable
- Looks like: a small box with the PR number on its top slides from one station to the next along the cable,
  enters the far block and is gone.
- How: an element (layer per the depth rule above) with `offset-path: path(cometPath(points, 0))` and
  `offset-rotate: 0deg` (the box stays upright instead of turning with the path); animate `offset-distance`
  0 to 100 percent once (a one-shot keyframe, or `motion` `animate(el, { offsetDistance: ['0%', '100%'] })`).
  Duration from route length, clamped (Munder: 230 px/s, 0.8 to 2.0 s). The box is a scaled `RoundedBox`
  from `components/buddy/` so it shares the light and walls of the buddies. `routeLink` and `cometPath` are
  private to `TileLinks.tsx` today and need exporting.
- From: the app (`iso-cable-comet`, `cometPath`); timing from Munder Difflin `MessageEnvelope.ts`.

### T2. Hop on an arc, with a burst on landing
- Looks like: a job or a message leaves the ground, flies in a low arc to a station that has no cable, and a
  thin ring opens where it lands.
- How: `motion` `animate` on two nested elements: the outer moves x and y linearly, the inner moves y by
  `-lift * sin(pi * t)` (keyframes `[0, -lift, 0]` with `ease: ['easeOut', 'easeIn']`). Landing ring: the
  reverse of `iso-hold-ring` (scale 0.6 to 1.6, opacity 1 to 0, 340 ms).
- From: Munder Difflin `MessageEnvelope.ts`.

### T3. Squash on landing, gulp on receipt
- Looks like: the crate flattens and widens for a beat when it lands; the receiving buddy stretches up and
  settles, like swallowing the job.
- How: crate `scale: 1.15 0.8` then back in 180 ms. Buddy: set `data-buddy-stretched` for about 250 ms; its
  rules use separate `translate` and `scale`, so the gulp adds to the bob instead of cutting it.
- From: the app (`[data-buddy-stretched]`, `iso-buddy-bob-*`); Vibecraft "happyBounce".

### T4. Copies of one coworker: budding and dissolving
- Looks like: when a coworker starts a second run, a smaller twin pops out of its top, hops to a free cell
  beside it, lands with a squash and starts working out of step with the parent. When a run ends, the copy
  hops back into the parent, which shudders once.
- How: the copy is a `TileBuddy` with a smaller `footprintShare` (for example 0.6), the same look, and a copy
  number on its wall. Its cell comes from a seat list around the station, first free cell first. Spawn: T2
  from the parent top to the cell, then T3. Out of step: `--buddy-delay` and `--buddy-blink-delay` from a
  hash of the copy id, the way `cableTiming` derives phase. Ceiling: empty sockets on the floor around the
  parent ("2 of 3" reads as two filled sockets of three).
- From: Munder Difflin `SeatPool.ts`; Pixel Agents `blink.ts` (own clock per character); Vibecraft mini
  copies at the portal; the app `cableTiming`.

### T5. A work loop per station
- Looks like: at the build station a buddy does a fast small shake (typing); at review its pupils scan left
  to right in three lines with a quick return (reading); at checks the light band on its top runs faster.
  You can tell the stage from the motion alone, and the word stays on the label.
- How: new values of `data-buddy-motion` (for example `type` and `read`) with their own keyframes in
  `styles.css`, next to `bob` and `shudder`. `read` animates `.iso-buddy-pupils` `translate` in the rhythm
  of `WorkingBehaviors.ts` (eighty percent of the line to scan, twenty percent to return).
- From: Vibecraft `WorkingBehaviors.ts`.

### T6. Idle acts picked at random, per buddy
- Looks like: a buddy with nothing to do now and then looks around, stretches tall, or nods off slowly.
- How: copy the pattern of the per-agent scheduler in `hooks/useLivingBoard.ts` (a demo beat for read-only
  boards: weighted pick, random dwell) into a scheduler of short one-shot idle acts, one every 6 to 14 s, only in the real idle state. Each act is a class added for
  its duration.
- From: Vibecraft `IdleBehaviors.ts`; the app `useLivingBoard.ts`.

### T7. A queue in front of each station
- Looks like: jobs waiting for a station stand as crates on the cells in front of its input face; when the
  first is taken, the others step forward one cell, one after another.
- How: queue cells are the last leg of the inbound route, walked backwards from the station face. Each crate
  has `transition: translate 300ms` and a delay of 40 ms times its place in line. A long line is the pile-up
  DESIGN.md wants visible; past five crates, show the fifth as a stack with a count.
- From: Claude Office `systems/queuePositions.ts`.

### T8. A station lights up while it is in use
- Looks like: the screen face of a station is dark when idle; when a copy works at it, it switches on, lines
  scroll and a cursor blinks; the floor light pool under it opens.
- How: two layers on the station face, the "on" layer faded in by opacity; scrolling lines as a
  `repeating-linear-gradient` with `background-position` animated; cursor `steps(2)` blink. Reuse
  `iso-tile-halo` and `iso-buddy-pool`.
- From: Munder Difflin `DeskScreen.ts`.

### T9. Bubble with a fade state machine
- Looks like: over a working copy, a small bubble with a sign and a target ("PR 312", "checks 3/7"); it stays
  while the action holds, lingers 1.2 s after, and fades.
- How: reuse `TileStatusBubble.tsx` and `TileToastBubble.tsx`; add the lingering state and a character cap.
  Waiting for a person gets its own bubble shape, not just a colour.
- From: Munder Difflin `ThoughtBubble.ts`, `ToolBubble.ts`; Pixel Agents waiting and permission bubbles.

### T10. Animate only what changed while watching, spread over the refresh window
- Looks like: on opening, everything is already in place, nothing flies. After that, when the next read shows
  that three jobs moved, the three moves play one after another over the next seconds, not all in one frame.
- How: diff two reads by job id; a job seen for the first time is placed with no flight. Moves found in one
  read are queued and started with a spacing of about 0.6 to 1.5 s (random per move), so a 30 s refresh still
  looks alive. Ended jobs leave the line only if the end was seen live.
- From: Claude Office `ExitingPeer.tsx` (only ends seen live); AI Town `useHistoricalTime.ts` (play the
  world a little in the past and spread the steps).

### T11. Materialise and dissolve by a sweep
- Looks like: a new job or station appears from the top down behind a bright line, the old one disappears
  the same way upward.
- How: one element with `clip-path: inset(0 0 100% 0)` animated to `inset(0)`, plus a 2 px light bar that moves
  down with it. The per-column stagger and flicker of the original are canvas pixel work; in the DOM one sweep
  with a faint `repeating-linear-gradient` over it is enough.
- From: Pixel Agents `matrixEffect.ts`.

### T12. The merge seal: flaps fold, a stamp drops
- Looks like: at the merge gate the crate lid folds shut flap by flap, a stamp comes down with an overshoot,
  the gate mark changes from a hollow to a filled circle, a small confetti puff goes up.
- How: flap elements with `transform-origin` on their hinge edge, all driven by one `--sealed` 0 to 1
  property, staggered by `--step` in `transition-delay`. Stamp: translateY with an overshoot easing, then T3
  on the crate. Confetti through `apps/ui/lib/confetti.ts` at the screen point of the gate, only for merges
  seen live (T10).
- From: Jhey Tompkins package toggle and printer articles.

### T13. Camera nudge toward an event
- Looks like: when something happens off-centre (a block, a merge), the view drifts a little toward it and
  settles; it never fights a drag.
- How: in `IsoGrid.tsx` pan state, ease the offset 40 percent of the way to the event over about 600 ms; skip
  while the user is dragging or has moved the camera in the last few seconds, and under reduced motion.
- From: Munder Difflin `Camera.ts` (lerp 0.08, nudge strength 0.4).

### T14. Ambient light carries a real number
- Looks like: the floor shifts from day to dusk as the plan window fills. Not used for a held line: in
  DESIGN.md section 4 a dimmed board already means "the delegator is not answering", and a held line keeps
  its light (the stopped belts and barrier of O1 say it).
- How: one board variable (for example `--iso-ambient`) on a background layer, changed with a 2 s transition;
  tiles and buddies keep their own light, so the shift reads as time, not as a fault.
- From: Claude Office `city/timeUtils.ts` (phases with progress); the trash-can stomp in
  `compactionAnimation.ts` is the same rule: a joke is fine when it is tied to a real value.

### T15. Belt surface that moves at the crate speed
- Looks like: belt cells between stations carry chevrons that run toward the next station, only while a crate
  is on that belt.
- How: a `repeating-linear-gradient` chevron on a cell clipped to the `DIAMOND` shape, `background-position`
  animated along the belt axis. Matching the texture speed to the crate speed of T1 is a judgement made here,
  not taken from a source. Crates on one belt are spacing along one path, not one object per cell.
- From: shapez.io patch notes, for items as spacing along one path (ideas only, GPL-3.0).

## Three objects that make a software factory read at a glance

### O1. The belt line with stations
- A belt of 1x1 cells joins the stations in order: build, review, checks, merge, with a short return belt
  from review back to build for "fix". Build and review are coworker buddies (the coder and reviewer types of
  DESIGN.md) with their copies around them (T4); checks and merge are machine tiles (O3, O2), not coworkers.
  Researcher and designer sit off the belt. Where "waiting on a job" stands (a siding beside the build
  input is one option) is left open.
- Jobs are crates with the PR number on the top face (T1); waiting jobs queue at the input face (T7); the belt
  runs only while a crate is on it (T15).
- Reads at a glance: where work piles up (the longest queue), which stage is busy (lit stations, T8), and that
  the line is moving at all. A held line stops every belt and drops a barrier arm across the inputs, next to the
  hold band DESIGN.md already has.

### O2. The merge gate
- A 2x2 arch at the end of the belt. A passing crate is sealed (T12) and slides onto an "ended today" shelf
  behind the gate, where crates stack by the hour.
- A blocked job does not pass: the arm stays down, the crate is turned aside onto a reject pad marked with
  the diamond of DESIGN.md and its reason in a bubble (T9). Failed, returned and rejected use the same pad with
  their own word.
- Reads at a glance: what shipped today (the height of the shelf) and what was refused (the pad).

### O3. The checks rack
- A tall 1x1 tile beside the checks station, like a server rack, with one light slot per check. Slots light
  one after another while checks run (`steps()`), a passed slot stays on, a failed slot turns into a small
  diamond and the rack shudders once (reuse `shudder`).
- Reads at a glance: how far the checks are and which one failed, without opening the job.

A fourth piece worth keeping from the flat mocks: the kanban of `mock-a.html` as a board on the back wall,
the way Claude Office hangs its kanban on a whiteboard. Clicking it opens the flat line. The receipt stays
available; it is just not the main picture.

## Verdict

STAY on DOM, CSS and `motion`; add no renderer. Every strong reference draws with canvas, PixiJS or Three.js,
but every technique above maps onto pieces the app already ships (`routeLink`, `cometPath`, `offset-path`,
hash-staggered timing, the buddy squash rules, `data-iso-paused`). PixiJS would buy speed with hundreds of
moving objects; the factory has tens (DESIGN.md sample: a few coworkers, three copies each, a handful of
jobs).

- Confidence: medium. Raised by a spike that measures frame time with 12 buddies, 10 crates and 4 belts
  moving at once, in a release build, on the laptop the owner uses.
- Not checked: how any reference looks in motion (code read only); whether `motion` `layoutId` would be a
  simpler way to move a crate between stations inside the panned and zoomed board (its docs did not confirm
  use across parents, and SVG is not supported), so T1 builds on `offset-path` instead.
- Next step: on top of the existing sample loop in `apps/ui/components/factory/factory-scene.ts`, replace the
  drop-in of a job with T1 + T3 on one route (build to review), add T7 at the review input and T4 for one
  copy; check by eye in light and dark at 1280x800 and 1920x1080, and measure frame time as above.
