# Open-source agent worlds, read at the code level
as_of 2026-11-14. Status: DRAFT, research only. No code in the repository was changed.

Companion to `INSPIRATION.md` in this folder (a parallel pass that covers Munder Difflin and the HN signal) and to
`docs/research/2026-11-14-factory-view/DESIGN.md`. This file answers one question: which motion techniques in open
projects that show AI agents as characters can be rebuilt in `packages/ui/src/iso-grid` with CSS keyframes, SVG or
`motion` v12, and are not there yet.

## How this was gathered

- Repositories were found with web search, then read with the GitHub API (`gh api .../contents`, trees) or a
  shallow sparse clone (since deleted). Nothing was run or installed. Every snippet below
  was copied from a file that was read, at the commit named for its project.
- **No motion was watched.** Timings are what the code says.
- Health figures: GitHub API, 2026-11-14. "Dormant" means no push for more than a year.
- **Licences.** Rerun is AGPL-3.0-only. MIT and Apache-2.0 code can be brought in with its notice kept; GPL-3.0
  (shapez.io) is also compatible with AGPL-3.0, but its code is canvas code and gives nothing to paste, so it is
  marked "technique only, reimplement". Sprites and tilesets are not covered by a code licence: borrow techniques,
  never art. No snippet is given from a repository with no licence or a NOASSERTION licence.
- Worked solo; no teammate agent was consulted.

## What iso-grid already has (so it is not listed again)

Read in `packages/ui/src/iso-grid` (`styles.css`, `components/TileBlock.tsx`, `TileBuddy.tsx`, `TileLinks.tsx`,
`TileHalo.tsx`, `TileToastBubble.tsx`, `TileStatusBubble.tsx`, `buddy/RoundedBox.tsx`, `types.ts`, `hooks/useLivingBoard.ts`):

| Present | Where |
|---|---|
| Fall-in landing with blur (`agent-drop-in`) | `styles.css:161`, `TileBlock.tsx:174` |
| Squash and stretch: top translate plus wall `scaleY` (bob, shudder), stretched when selected | `styles.css:204-272` |
| Floor pool (multiply in light, screen in dark) that dims as the top rises; contact shadow | `styles.css:173-179, 275` |
| Light band across a working top; face shimmer strips | `styles.css:281` (`iso-buddy-sweep`), `TileBlock.tsx:223-268` |
| Blink on a fixed 4.6 s period with a hashed phase; pupil glance on 7.3 s, only for a buddy alone in a page (`data-buddy-alive`), never on a board | `styles.css:290-316`, `TileBuddy.tsx:139-140` |
| Name and status rolling in one label; toast and status bubbles rising from the tile | `styles.css:191-199, 336-358` |
| Comet on cables via `offset-path`, per-cable period/phase from a hash, travel and rest carried by `linear()` easing | `styles.css:365-375, 455-482`, `TileLinks.tsx:320-355` |
| Cable drawing itself, dashed beam current, beam ring around the selection | `styles.css:379-403`, `BeamRing.tsx` |
| Ping rings (scale 1 to 1.6), error pulse, waiting dots, status spinner | `styles.css:134-155, 344` |
| Light walls breathing around a highlighted tile (opacity only, because of the blend layer) | `TileHalo.tsx`, `styles.css:147` |
| A scheduler per agent with weighted next state and random dwell | `hooks/useLivingBoard.ts` |
| Pause when unseen and reduced-motion cuts | `styles.css:325-332, 407-411` |

What the factory scene does today (`apps/ui/components/factory/factory-scene.ts`, commit `9d223a3`): a job is a new
tile per stage, `id: job-<issue>-<stage>` with `justPlaced: true` (`factory-scene.ts:125-133`), so it **drops in
beside its holder at every stage instead of travelling**. A copy is the same buddy at `opacity: 0.6`
(`factory-scene.ts:139`), with no entrance and no behaviour of its own. (The file's header says the job "travels
Dispatch -> Build -> Review -> Dispatch"; the code re-creates it per stage, so the header describes intent.) The techniques below are ranked by how
directly they close those two gaps.

Constraints every technique is held to, all taken from comments in the code:
1. A CSS class in `styles.css`, so `[data-iso-paused]` and `prefers-reduced-motion` reach it (no rAF loop, no SMIL).
2. No per-element blur or backdrop filter on things that repeat (`styles.css:181-182`: 150 frosted labels cost three
   frames out of four).
3. No `transform` on the layer that carries a blend mode (`styles.css:145-146`).
4. A buddy's base never leaves its cells (`styles.css:201-203`).
5. `factoryScene(t)` is a pure function of time, so every `Math.random` in a source becomes `hashUnit(id, salt)`
   (`iso.ts:89`), and every one-off motion is anchored by a stable negative `animation-delay`, as the comet does.
6. On a board, eyes do not glance (`styles.css:299-302`): one buddy alone in a page is alive, twenty at once are
   noise. Anything that moves the eyes must say why the factory may break this.

## Ranked projects

| # | Project | Licence | Stars | Last push | Trajectory | Read at |
|---|---|---|---|---|---|---|
| 1 | [pixel-agents-hq/pixel-agents](https://github.com/pixel-agents-hq/pixel-agents) | MIT | 10.2k | 2026-11-10 | rising | `4dd14d612f` |
| 2 | [sebastianwessel/isostate](https://github.com/sebastianwessel/isostate) | MIT | 5 | 2026-10-13 | new, one author | `f1e44a17b8` |
| 3 | [Nearcyan/vibecraft](https://github.com/Nearcyan/vibecraft) | MIT | 1.5k | 2026-01-18 | stalled (10 months) | `8278a4bc33` |
| 4 | [OpenBMB/ChatDev](https://github.com/OpenBMB/ChatDev) (2.0 web UI) | Apache-2.0 | 34.7k | 2026-11-06 | stable | `464a681ba7` |
| 5 | [tobspr-games/shapez.io](https://github.com/tobspr-games/shapez.io) | GPL-3.0 | 7.0k | 2026-09-07 | stable, maintenance | `8a79de5255` |
| 6 | [paulrobello/claude-office](https://github.com/paulrobello/claude-office) | MIT | 616 | 2026-11-11 | rising | `978b134504` |
| 7 | [a16z-infra/ai-town](https://github.com/a16z-infra/ai-town) | MIT | 10.8k | 2026-11-05 | stable | `1b2f7d8b82` |
| 8 | [joonspk-research/generative_agents](https://github.com/joonspk-research/generative_agents) | Apache-2.0 | 22.4k | 2024-08-05 | dormant | `fe05a71d3e` |

Why this order: rank follows how much of the code can be rebuilt as DOM/CSS for the two gaps above, not stars.
isostate has five stars but is the only project here that is already SVG plus CSS on an isometric grid, so its code
is nearly drop-in; pixel-agents is the only one that already models sub-agents as companions of a lead.
Munder Difflin (HarnessMD/munder-difflin, MIT, 9.5k stars, pushed 2026-11-14) is read in `INSPIRATION.md`; its
arcing message envelope is the other strong reference for a travelling job and is not repeated here.

Metadata only, source not read (so no animation files are claimed): OpenHands/OpenHands (MIT, 93k, a chat and
workspace UI, no world), FoundationAgents/MetaGPT (MIT, 71k), OpenBMB/AgentVerse (Apache-2.0, 5.2k, dormant since
2024-09), pixtuoid/pixtuoid (MIT, 560, a terminal app in Rust), Gaurav2693/ai-office (MIT, 69, Three.js),
arturitu/the-delegation (NOASSERTION, 731), zep-ia/pixel-agent-desk (NOASSERTION, 138), elchininet/isometric-css
(Apache-2.0, 75) and MorganCaron/IsometricSass (MIT, 396, dormant since 2023; both only project boxes, which
iso-grid already does). claude-squad was not looked up. ChatDev's old "visualizer" is gone from the 2.0 tree; the
walker below is in the new Vue UI.

### 1. pixel-agents (VS Code extension, canvas 2D)
Each Claude Code session is a pixel character in an office; sub-agents are separate characters. All motion lives in
`webview-ui/src/office/engine/`.

- **Helpers that stay with their lead** - `characters.ts:347-422` `updateHelper`, `atHome`, `wantsState`. A sub-agent
  has no chair and never wanders: it stays within `HELPER_FOLLOW_RADIUS_TILES = 2` of its lead's seat, walks back
  when the lead moves, faces the lead's way, sits while it works and **stands only after 3 s idle**
  (`HELPER_STAND_UP_DELAY_SEC`), so the gap between two tool calls does not flip its pose.
- **Matrix spawn and despawn** - `matrixEffect.ts:31-132`. A bright head sweeps down each pixel column, columns
  staggered by a seed, revealing the sprite under a fading green trail; despawn eats it the same way. 0.3 s.
- **Blinks out of step** - `blink.ts:23-52`. Exponential gaps (floor 1.5 s, mean 3.5 s, cap 11 s), 15 % double
  blinks, gaps stretched 1.5x while working.
- **Ghost for headless agents** - `renderer.ts:409-411`: translucent when the agent has no terminal.
- **Pop** - `webview-ui/src/index.css:415-431` `pixel-pop`, 280 ms, 1 to 0.7 to 1.2 to 1.
- Walk: 4 frames at 0.15 s, 48 px/s, linear tile-to-tile interpolation (`characters.ts:305-325`); a path search on the
  tile map (`layout/tileMap.js`, not read). Not needed: iso-grid buddies do not walk.

```ts
// pixel-agents, MIT, webview-ui/src/office/engine/characters.ts:402-409 (4dd14d612f)
/** Sitting while working, standing while waiting. The gap between two tool
 *  calls is not waiting: standing up and sitting back down every few seconds
 *  swaps the seated sprite for the standing one and back, so a helper stands
 *  only once it has been idle for HELPER_STAND_UP_DELAY_SEC. */
function wantsState(ch: Character): CharacterState {
  const working = ch.isActive || ch.helperIdleSec < HELPER_STAND_UP_DELAY_SEC;
  return working ? CharacterState.TYPE : CharacterState.IDLE;
}
```

```ts
// pixel-agents, MIT, webview-ui/src/office/engine/blink.ts:22-52 (excerpt)
export function blinkGap(focused: boolean, rand: Rand = Math.random): number {
  const wait = -Math.log(1 - rand()) * BLINK_GAP_MEAN_SEC;
  const gap = Math.min(BLINK_GAP_MIN_SEC + wait, BLINK_GAP_MAX_SEC);
  return focused ? gap * BLINK_FOCUS_STRETCH : gap;
}
...
  b.blinkShut = between(BLINK_SHUT_SEC, rand);
  // The next wait starts once the eyes open again (blinkIn doesn't run while shut).
  b.blinkIn =
    rand() < BLINK_DOUBLE_CHANCE ? between(BLINK_DOUBLE_GAP_SEC, rand) : blinkGap(focused, rand);
```

```ts
// pixel-agents, MIT, webview-ui/src/office/engine/matrixEffect.ts:44-69 (excerpt)
  for (let col = 0; col < MATRIX_SPRITE_COLS; col++) {
    // Stagger: each column starts at a slightly different time
    const stagger = (ch.matrixEffectSeeds[col] ?? 0) * MATRIX_COLUMN_STAGGER_RANGE;
    const colProgress = Math.max(
      0,
      Math.min(1, (progress - stagger) / (1 - MATRIX_COLUMN_STAGGER_RANGE)),
    );
    const headRow = colProgress * totalSweep;
    for (let row = 0; row < MATRIX_SPRITE_ROWS; row++) {
      ...
      if (isSpawn) {
        // Spawn: head sweeps down revealing character pixels
        if (distFromHead < 0) {
          // Above head: invisible
          continue;
        } else if (distFromHead < 1) {
          // Head pixel: bright white-green
          ctx.fillStyle = MATRIX_HEAD_COLOR;
```

### 2. isostate (scroll-driven isometric scenes, SVG plus CSS)
The nearest stack to iso-grid: an SVG isometric scene whose connectors carry message tokens.

- **Upright tokens on a path** - `packages/core/src/rendering/animation-css.ts:36-37, 42`: tokens ride
  `offset-path` with `offset-rotate: 0deg`, so an isometric parcel stays upright on the turns instead of pivoting the
  way the comet's trail does. Reduced motion parks each token at `offset-distance: 50%`, which still shows a job is
  on that link.
- **N tokens on one keyframe** - `scene-effects.ts:106-127` `updateMessages`: `animationDelay = -duration * i / count`
  spreads them evenly; the path is updated in place, so a re-route does not restart their progress.
- **Parcel art in three faces** - `scene-effects.ts:81-103` `messageToken`: shadow ellipse, top, left and right faces
  as three paths, a white edge highlight.
- **Glow without a filter** - `scene-effects.ts:43-78` `updateTrackEffects`: a wider stroke (+8 px) at 16 % opacity
  under the shaft, and a thin white core at 70 % over it.
- **Activity breathing** - `animation-css.ts:38-40`: ring 1.8 s, waiting badge 2.6 s (iso-grid has the same idea).

```ts
// isostate, MIT, packages/core/src/rendering/animation-css.ts:36-37, 42 (f1e44a17b8)
"@keyframes iso-message-travel{from{offset-distance:0%}to{offset-distance:100%}}",
".iso-message{offset-anchor:0px 0px;offset-rotate:0deg;animation:iso-message-travel 1800ms linear infinite;pointer-events:none}",
"@media (prefers-reduced-motion:reduce){.iso-message{animation:none!important;offset-distance:50%}.iso-activity *{animation:none!important}}",
```

```ts
// isostate, MIT, packages/core/src/rendering/scene-effects.ts:105-126 (excerpt)
/** Update motion paths in place so rerouting does not restart packet progress. */
export function updateMessages(node: SVGGElement, def: RuntimeConnectorState, d: string, recreate: boolean): void {
	...
		for (let i = 0; i < count; i++) {
			const token = shape("g", { class: "iso-message", "aria-hidden": "true", "data-kind": message.kind ?? "packet" });
			token.style.animationDuration = `${duration}ms`;
			token.style.animationDelay = `${(-duration * i) / count}ms`;
			token.appendChild(messageToken(message.kind ?? "packet", message.size ?? 10, message.color ?? def.style.stroke));
			node.appendChild(token);
		}
	...
	for (const token of node.querySelectorAll<SVGGElement>(".iso-message")) {
		token.style.offsetPath = `path("${d}")`;
		token.style.animationDirection = def.direction === "reverse" ? "reverse" : "normal";
```

### 3. vibecraft (Three.js isometric workshop for Claude Code)
Claude walks between stations by tool; sub-agents are "mini-Claudes" (scale 0.6, `src/entities/SubagentManager.ts:50-55`)
that start at a portal station.

- **A behaviour per tool** - `src/entities/animations/WorkingBehaviors.ts`. Reading (`:31-70`): eyes scan three lines
  per 4 s cycle, 80 % of each line slow left to right, 20 % quick return, a page flip at mid-cycle. Typing
  (`:154-180`): two arms half a cycle apart, 12 cycles per 2 s. Also scanning, channelling (glow pulse), checking tasks.
- **Event burst** - `src/scene/WorkshopScene.ts:2002-2016` (5 particles per tool use, upward speed 2-4, sideways
  plus or minus 1) and `:2505-2531` (gravity 5, hidden below the floor; the station ring pulses
  `scale 1 + 0.05 x I` with I decaying 0.5 per second).
- **Rising notice** - `src/scene/ZoneNotifications.ts:211-222`: ease-out rise, full opacity until 60 %, then a
  quadratic fade.

```ts
// vibecraft, MIT, src/entities/animations/WorkingBehaviors.ts:42-50 (8278a4bc33)
    // Eyes scan left to right (reading)
    const readCycle = progress * 3  // 3 lines per cycle
    const lineProgress = readCycle % 1
    const eyeX = (lineProgress < 0.8)
      ? -0.02 + easeInOut(lineProgress / 0.8) * 0.04  // Read left to right
      : 0.02 - easeOut((lineProgress - 0.8) / 0.2) * 0.04  // Quick return

    parts.leftEye.position.x = -0.07 + eyeX
    parts.rightEye.position.x = 0.07 + eyeX
```

```ts
// vibecraft, MIT, src/scene/WorkshopScene.ts:2006-2014 and 2522-2531 (excerpts)
        positions[i * 3] = (Math.random() - 0.5) * 2
        positions[i * 3 + 1] = 0.5
        positions[i * 3 + 2] = (Math.random() - 0.5) * 2

        // Random upward velocity with spread
        velocities[i * 3] = (Math.random() - 0.5) * 2
        velocities[i * 3 + 1] = 2 + Math.random() * 2
        velocities[i * 3 + 2] = (Math.random() - 0.5) * 2
...
            positions[i * 3 + 1] += velocities[i * 3 + 1] * delta
            // Apply gravity
            velocities[i * 3 + 1] -= 5 * delta
            // Fade out when falling
            if (positions[i * 3 + 1] < 0) {
              positions[i * 3 + 1] = -1000 // Hide far below
```

### 4. ChatDev 2.0 (Vue workflow UI)
When a message crosses an edge of the workflow graph, the sending agent's sprite **walks the edge**.

- `frontend/src/pages/LaunchView.vue:1996-2090` `animateSpriteAlongEdge`: the sprite is an SVG `<image>` in the edge's
  own SVG; duration `min(max(length * 0.02, 2000), 4000)` ms, which on any real edge is a flat 2 s; it faces left or right by comparing the two end points; walk
  frames 1-2-1-3 every 250 ms; removed at the end.
- `frontend/src/components/WorkflowEdge.vue:182-205` `runEdgeAnimation`: a running edge gets a dash flow plus a
  separate stroke-opacity pulse of 4 s (half a fixed 8 s), both through the Web Animations API.

```js
// ChatDev, Apache-2.0, frontend/src/pages/LaunchView.vue:2043-2067 (464a681ba7, excerpt)
  const startPoint = pathElement.getPointAtLength(0)
  const endPoint = pathElement.getPointAtLength(pathLength)
  const direction = endPoint.x >= startPoint.x ? 'R' : 'L'

  // Animation duration based on path length (longer paths = more time)
  const duration = Math.min(Math.max(pathLength * 0.02, 2000), 4000) // 2-5 seconds
  ...
  const animate = (timestamp) => {
    if (!startTime) startTime = timestamp
    const elapsed = timestamp - startTime
    const progress = Math.min(elapsed / duration, 1)
    const point = pathElement.getPointAtLength(progress * pathLength)
    spriteImage.setAttribute('transform', `translate(${point.x}, ${point.y})`)
    // Update walking animation frame: 1 -> 2 -> 1 -> 3 -> repeat
    const frameIndex = Math.floor(elapsed / 250) % 4
```

### 5. shapez.io (factory game, canvas) - technique only, reimplement
- **Back-pressure with a minimum gap** - `src/js/game/belt_path.js:1129-1186` `update`: items are stored as gaps to the
  next item; each tick the belt's travel is shared from the front item backwards, and no item may come closer than
  `itemSpacingOnBelts` to the one ahead. When the end is blocked, items stop one gap apart and the queue is visible.
- **Belt surface tied to item speed** - `src/js/game/systems/belt.js:505-511`: the 14-frame belt animation index is
  derived from the clock times the same belt speed and item spacing the items use ("SYNC with item_acceptor"), so a
  moving item and the surface under it travel at one speed. The surface keeps running under blocked items; stopping
  it on a hold is not in shapez.
- **Cheap mode** - `belt.js:515-537`: with "simplified belts" only the hovered belt animates.

```js
// shapez.io, GPL-3.0, src/js/game/belt_path.js:1162-1177 (8a79de5255). Technique only.
            // Compute how much spacing we need at least
            const minimumSpacing =
                lastItemProcessed === this.items.length - 1 ? 0 : globalConfig.itemSpacingOnBelts;

            // Compute how much we can advance
            let clampedProgress = nextDistanceAndItem[0 /* nextDistance */] - minimumSpacing;

            // Make sure we don't advance more than the remaining velocity has stored
            if (remainingVelocity < clampedProgress) {
                clampedProgress = remainingVelocity;
            }

            // Make sure we don't advance back
            if (clampedProgress < 0) {
                clampedProgress = 0;
            }
```

### 6. claude-office (Next.js, PixiJS)
A boss character is the main agent; sub-agents arrive by elevator, queue at the boss in numbered slots (arrival and
departure queues; phases in `frontend/src/machines/agentMachine.ts`: `in_arrival_queue`, `walking_to_ready`,
`conversing`, `walking_to_desk`, `in_departure_queue`, `in_elevator`), work at desks and leave.

- **Typing arms out of phase** - `frontend/src/components/game/AgentSprite.tsx:276-279`: `sin(t*8)` and
  `sin(t*8 + 0.7*pi)`.
- **Day and night from the real clock** - `frontend/src/components/game/city/timeUtils.ts:73-92` `computeTimeState`:
  seasonal dawn and dusk windows, a 0-1 progress inside each; `city/skyRenderer.ts:32-48` `lerpColor` mixes palettes
  by it; stars fade in at night.
- **Doors** - `frontend/src/components/game/Elevator.tsx:50-79`: ease-out cubic on the door scale over a fixed time.

```ts
// claude-office, MIT, frontend/src/components/game/city/timeUtils.ts:73-92 (978b134504)
export function computeTimeState(hour: number, date: Date): TimeState {
  const [dawnStart, dawnEnd, duskStart, duskEnd] = getSeasonalTimes(date);

  if (hour >= duskEnd || hour < dawnStart) {
    return { hour, progress: 0, phase: "night" };
  }

  if (hour >= dawnStart && hour < dawnEnd) {
    const progress = (hour - dawnStart) / (dawnEnd - dawnStart);
    return { hour, progress, phase: "dawn" };
  }

  if (hour >= dawnEnd && hour < duskStart) {
    return { hour, progress: 0, phase: "day" };
  }

  // Dusk transition
  const progress = (hour - duskStart) / (duskEnd - duskStart);
  return { hour, progress, phase: "dusk" };
}
```

### 7. AI Town (Convex, PixiJS)
- **Play the world a little behind the data** - `src/hooks/useHistoricalTime.ts:59-123`: the client keeps a buffer of
  server step intervals and renders at a "historical" time about one step behind, running its clock at 0.8x when the
  buffer is short and 1.2x when it is long, jumping only if more than 1.5 s behind. Positions are then read from the
  per-field sample history (`src/hooks/useHistoricalValue.ts`), so movement between server steps is continuous.
- Speech and thought are single glyphs over the head (`src/components/Character.tsx:88-106`); a destination ring
  grows over 500 ms (`src/components/PositionIndicator.tsx`), the same idea as iso-grid's ping rings.

```ts
// ai-town, MIT, src/hooks/useHistoricalTime.ts:71-85 (1b2f7d8b82)
    // Simple rate adjustment: run time at 1.2 speed if we're more than 1s behind and
    // 0.8 speed if we only have 100ms of buffer left. A more sophisticated approach
    // would be to continuously adjust the rate based on the size of the buffer.
    const bufferDuration = lastServerTs - prevServerTs;
    let rate = 1;
    if (bufferDuration < SOFT_MIN_SERVER_BUFFER_AGE) {
      rate = 0.8;
    } else if (bufferDuration > SOFT_MAX_SERVER_BUFFER_AGE) {
      rate = 1.2;
    }
    let serverTs = Math.max(
      prevServerTs + (clientNow - prevClientTs) * rate,
      // Jump forward if we're too far behind.
      lastServerTs - MAX_SERVER_BUFFER_AGE,
    );
```

### 8. Generative Agents / Smallville (Django plus Phaser), dormant
`environment/frontend_server/templates/home/main_script.html:428-502`: each backend step moves a persona one tile, x
first and then y, in fixed sub-steps, and a "pronunciatio" balloon (initials plus an emoji of the current action)
follows the sprite. Both are already in iso-grid in a better form: cables route along the two iso axes
(`TileLinks.tsx` `routeLink`) and the label rolls between name and status. Listed for completeness; nothing new to
take.

```js
// generative_agents, Apache-2.0, environment/frontend_server/templates/home/main_script.html:440-454 (fe05a71d3e)
      if (execute_count == execute_count_max) {
        let curr_x = execute_movement["persona"][curr_persona_name]["movement"][0];
        let curr_y = execute_movement["persona"][curr_persona_name]["movement"][1];
        movement_target[curr_persona_name] = [curr_x * tile_width,
                                              curr_y * tile_width];
        let pronunciatio_content = execute_movement["persona"][curr_persona_name]["pronunciatio"];
        // This is what gives the pronunciatio balloon the name initials. We
        // use regex to extract the initials of the personas.
        // E.g., "Dolores Murphy" -> "DM"
        let rgx = new RegExp(/(\p{L}{1})\p{L}+/, 'gu');
        let initials = [...curr_persona_name.matchAll(rgx)] || [];
        initials = (
          (initials.shift()?.[1] || '') + (initials.pop()?.[1] || '')
        ).toUpperCase();
        pronunciatios[curr_persona_name].setText(initials + ": " + pronunciatio_content);
      }
```

## Techniques to add to iso-grid (not there today)

Ordered by value to the factory view. "Upgrade" marks a change to something that exists. Line counts are rough.

### A. Jobs that travel

**1. A parcel that rides the cable** (isostate). A job is an upright isometric box on the link's `offset-path`,
with `offset-rotate: 0deg`, so it stays upright on the elbow.
- `types.ts:246`: `TileLink` gains `parcels?: { id: string; color?: string; startMs: number; durationMs: number }[]`.
- `TileLinks.tsx`, in the HTML layer next to the comet (`:320-355`, which already builds `cometPath(points, ...)`):
  one `<div className="iso-parcel">` per parcel with `offsetPath`, holding a 16 px SVG of three faces (top, left,
  right) like isostate's `messageToken`. About 30 lines.
- `styles.css`, next to `.iso-cable-comet`: `@keyframes iso-parcel-run { from { offset-distance: 0% } to {
  offset-distance: 100% } }`; `.iso-parcel { offset-rotate: 0deg; offset-anchor: 50% 85%; animation: iso-parcel-run
  var(--d) cubic-bezier(.45,0,.2,1) var(--delay) both }`; the same `@supports` guard as the comet; under reduced
  motion `animation: none; offset-distance: 100%` (isostate parks at 50 %; for a hand-off the end is the truth).
  About 15 lines.
- Depth: the parcel crosses cells, so it lives in the link layer above the floor, not in a tile (`iso.ts` `tileZ`
  sorts tiles by cell).

**2. Hand-off instead of drop-in** (ChatDev walker, isostate in-place path). In `factory-scene.ts` the job tile is
re-created per stage (`id: job-<issue>-<stage>`, `justPlaced: true`). Keep one id per job (`job-<issue>`) so the tile
is never re-mounted, and at each stage change emit a parcel on the link from the old holder to the new one,
`durationMs = clamp(1200, length * 9, 2600)` (ChatDev's clamp is a flat 2 s in practice; here the length should count). The
job tile is hidden while the parcel runs (`opacity: 0` with a 150 ms transition) and reappears where it lands, so the
eye follows one object.
- Pure time: compute the delay once, when the parcel mounts, as `-(t - startMs)`, and hold it in a ref; from then on
  the CSS clock carries the run, so later renders neither restart nor shift it. Never recompute it on each render.
- Optional deformation on arrival: play `iso-buddy-shudder-*` once on the receiving buddy
  (`animation-iteration-count: 1`); it already reads as a gulp.
- About 25 lines in `factory-scene.ts`, nothing in iso-grid beyond item 1.

**3. A queue with back-pressure** (shapez, reimplemented). Jobs waiting for a reviewer, or held by a sending hold, do
not ring the delegator one by one; they stand on the incoming cable one gap apart, nearest the station first:
`offset-distance: calc(100% - (var(--i) + 1) * var(--gap))` with `transition: offset-distance 600ms
cubic-bezier(.22,1,.36,1)`, so when the head leaves the others close up. claude-office's numbered queue slots are the
same idea.
- Same `.iso-parcel` element with `data-parked` and `--i` from the job's place in the queue. About 10 lines CSS, 15
  in `factory-scene.ts` (which already orders waiting jobs, `factory-scene.ts:38`).

**4. One speed for the current and the parcels** (shapez belt sync; upgrade of `iso-link-current`). The dash current
runs at a fixed 1.2 s (`styles.css:401-403`). Drive the dash and the parcels from one custom property
`--iso-belt-speed`: dash `animation-duration: calc(var(--iso-belt-period-s) / var(--iso-belt-speed))` (both properties new;
`--iso-belt-period-s` starts at today's 1.2 s), parcel duration from the same value. When the line is held, pause the belt (Rerun's own addition; shapez keeps its belts running)
(`[data-held] .iso-link-current { animation-play-state: paused }`): the whole belt visibly stops and the parked queue
of item 3 stays. About 8 lines CSS.

**5. Glow without a filter on links** (isostate; upgrade). `TileLinks.tsx:236-238` defines `agentlink-glow` with
`feGaussianBlur stdDeviation="2"`. With dozens of live cables, draw instead a second path under each glowing link at
`strokeWidth + 6`, `strokeOpacity: 0.16`, round caps, and a hairline white core over it at 0.7. No filter is
rasterised. About 12 lines in `TileLinks.tsx`. Same idea for `BeamRing.tsx:39`, which blurs the beam with CSS.

### B. Copies that are alive

**6. A copy that materialises from its main** (pixel-agents matrix effect). Replace the drop-in for copies with a
reveal: a 2 px bright bar falls down the buddy while a mask uncovers the body behind it; leaving runs it backwards.
Register `@property --iso-reveal { syntax: '<percentage>'; initial-value: 0%; inherits: false }` (the file already
registers `--iso-shine-angle`, `styles.css:523`), animate it from 0 % to 100 % in 450 ms, and set on the copy's art
wrapper `mask-image: linear-gradient(to bottom, #000 var(--iso-reveal), transparent calc(var(--iso-reveal) + 6%))`;
the bar is a sibling `div` with `translate: 0 var(--iso-reveal)`. Four vertical strips with `hashUnit`-seeded delays
give the staggered columns if one sweep looks too clean.
- `TileBuddy.tsx`: a `data-buddy-arrive` / `data-buddy-leave` attribute on the art wrapper; the mask never goes on the
  pool layer (constraint 3). About 25 lines CSS, 6 TSX.
- A copy that leaves keeps its tile for 450 ms after its job ends; `factory-scene.ts` emits it with a `leaving` flag.

**7. Copies that look like copies, not faded buddies** (pixel-agents headless ghost; vibecraft mini-Claude at 0.6).
Today a copy is the whole tile at `opacity: 0.6`, which also fades its face and its floor pool. Instead:
`BuddyLook.footprintShare` (`types.ts:100-102`, already supported) at about 0.7 so a copy is smaller than its main,
and a `[data-buddy-copy]` rule: walls `opacity: .35` (select `.iso-buddy-wall:not(.iso-buddy-painted)`: the painted face carries the
wall class too, `buddy/RoundedBox.tsx:70`), top `.55`, face and label at full, pool at half strength. The
eyes and the bob stay readable; the body reads as see-through. About 12 lines CSS, a prop in `TileBuddy.tsx`, and
the flag set at `factory-scene.ts:139` instead of `opacity: 0.6`.

**8. Sticky "working" between tool calls** (pixel-agents `HELPER_STAND_UP_DELAY_SEC`). A coworker between two tool
calls is not idle. When live data drives the board, hold the mood `working` for 3 s after work stops, so the bob does
not stutter every few seconds. In the pure scene this is `working = t < lastWorkEndMs + 3000`. About 6 lines in the
scene, or where the mood is chosen (`buddyMood`, `components/buddy/buddy-look.ts:43`).

**9. A behaviour per tool** (vibecraft). Only `bob` exists for working (`TileBuddy.tsx:19`). Add three motions keyed
on `data-buddy-work`. A rule in the code stands in the way and must be decided first: pupils and lids move only for a
buddy that is `alive` (`styles.css:299-316`; set only by `buddy/AgentBuddy.tsx:64`, never by `TileBuddy`), because
"twenty buddies on a board glancing at once is noise, not life", and pupils exist only for the `googly` eye
(`buddy/BuddyFace.tsx:186-196`). The owner's "they all move" argues for opting the factory board in, but only for
buddies whose current tool is reading, so the room never glances in unison. For the `dot` eye, move the whole
`.iso-buddy-eyes` group with the `translate` property, which leaves its blink `transform` alone:
- `read` (search, reading files, review): the pupils (googly) or the eye group (dot) run a sawtooth, three lines per 4 s, slow to the right for 80 % of
  each line and back in 20 %: `@keyframes iso-buddy-read { 0% { translate: -1px .4px } 26.7% { translate: 1px .4px }
  33.3% { translate: -1px .4px } ... }` on `.iso-buddy-pupils` or `.iso-buddy-eyes`, with a slower, smaller bob.
- `type` (writing code): a short fast bob (0.4 s, 6 % of depth instead of 20 %) plus a side shift of the top,
  `translate: +-0.6px 0`, half a period out of step with the bob (claude-office's arms at `0.7*pi`, vibecraft's at
  half a cycle). The side is one surface (`buddy/RoundedBox.tsx:77-80`), so the alternation goes on the top, not on
  two walls.
- `scan` (checks): `iso-buddy-sweep` at twice the speed and, where the board is opted in, a left-right-only glance.
- `styles.css` near `:303-316`, about 30 lines; `TileBuddy.tsx` a `work` prop next to `MOTION`; the tool taxonomy
  in the scene, the way pixel-agents uses `isReadingToolName`.

**10. Blinks out of step, with doubles** (pixel-agents; upgrade). Every buddy blinks every 4.6 s today (`.iso-buddy-eyes` on
every board; `.iso-buddy-lids` only when `alive`), only the phase differs (`TileBuddy.tsx:140`). CSS cannot draw a new random gap each cycle, but it can (a) give each buddy its own
period from `hashUnit(id, 13)` between 3.5 and 7 s through `--buddy-blink-period`, (b) give about 15 % of buddies a
second keyframe set with a double blink (`92% 1, 94% .08, 96% 1, 97.5% .08, 99% 1`), and (c) stretch the period 1.5x
while working (`calc(var(--buddy-blink-period) * 1.5)` under `[data-buddy-motion='bob']`). About 12 lines CSS, 3 TSX.

### C. Events that are felt

**11. A pop when a stage passes** (pixel-agents `pixel-pop`). A one-shot 280 ms squash on the job object when checks
pass or the PR merges: `@keyframes iso-pop { 0% { scale: 1 } 30% { scale: .8 1.1 } 65% { scale: 1.12 .92 } 100% {
scale: 1 } }`, on the `scale` property so it adds to any running transform (the reason given at `styles.css:243-244`).
Restart it by changing a `data-pop` key. About 8 lines CSS, 4 in `TileBlock.tsx`.

**12. A burst of sparks and a station pulse** (vibecraft). On merge, five sparks leave the station and fall back.
Each spark is two nested spans: the outer moves sideways linearly (`--dx` from `hashUnit`, plus or minus 10 px), the
inner goes up with ease-out to 40 % and down with ease-in to 100 % (a parabola without JS), fading in the last third;
700 ms. The station's ring scales once to 1.05 and settles (vibecraft's decaying `1 + 0.05 x I`).
`apps/ui/lib/confetti.ts` already wraps `canvas-confetti`, but that draws on a full-page canvas and does not obey
`[data-iso-paused]`; CSS sparks stay in the board's layer. New `components/TileBurst.tsx` about 35 lines, CSS about 20.

**13. A rising count** (vibecraft notice; a variant of the toast). A plate-less `+1` or `merged` rising 18 px off the
merge station: ease-out rise, full opacity until 60 %, then fade (`@keyframes iso-rise { 0% { translate: 0 0; opacity:
1 } 60% { opacity: 1 } 100% { translate: 0 -18px; opacity: 0 } }` with `cubic-bezier(.33,1,.68,1)`). It differs from
`TileToastBubble` (a plate that holds and leaves) because it needs no reading. About 10 lines CSS, and a
`kind: 'rise'` on the scene's toasts.

### D. The world around them

**14. Daylight from the real clock** (claude-office `computeTimeState`). One board-level custom property
`--iso-daylight` (0 night to 1 day, with dawn and dusk ramps) set once a minute in `IsoGrid.tsx` on the root, read by
two rules: a full-board tint layer, `background: color-mix(in oklab, #1b2a6b calc((1 - var(--iso-daylight)) * 18%),
transparent)` with `mix-blend-mode: multiply` (a sibling layer, no transform), and buddy pools that grow at night
(`opacity: calc(var(--iso-pool-strength) * (1.4 - .4 * var(--iso-daylight)))`, both properties new; today the
pool strength is a per-mood number, `POOL_STRENGTH` in `TileBuddy.tsx`), so at night the floor is lit by the workers. The
factory is dark by default (commit `9d223a3`): keep the tint under 20 % so it never fights the theme, and leave it
off on the template boards. About 15 lines CSS, 15 TSX.

**15. Play live data one beat behind** (AI Town). The live page will refresh about every 30 s (DESIGN.md section 5).
If the scene renders "now", every refresh makes jobs jump. Render instead at `t = now - beat` and take positions
from the ledger's `transitions` timestamps (`tools/factory/store.py`), so each hand-off of item 2 plays at its real
time within the last beat. If data is late, run the scene clock at 0.8x; if far behind, jump (AI Town jumps when more than
1.5 s behind). The scene is already a pure function of `t`, so this is a change in `FactoryWorld.tsx` (`:16-24`) only,
about 20 lines. Cost: the view is up to one beat late, which the header must say.

## What not to borrow
- Walking with sprite frames and pathfinding (pixel-agents, ChatDev, Smallville): iso-grid buddies are blocks whose
  base never leaves its cells. Movement on the board is carried by parcels on cables, which keeps that rule.
- Canvas particle systems and bloom passes (vibecraft, Three.js): rebuilt as items 5 and 12 instead.
- Per-frame JS loops (`requestAnimationFrame` in ChatDev, AI Town, claude-office): they escape `[data-iso-paused]`
  and reduced motion. Where `motion`'s `animate()` is used, keep it to one-shot runs and check reduced motion first.

## Open questions
- `offset-path` with `offset-rotate: 0deg` inside the board's scaled camera was not tried here; the comet proves
  `offset-path` works in that layer, not that an upright parcel stays crisp at every zoom.
- Whether a mask on the copy's art wrapper (item 6) disturbs the pool's blend: the pool must stay outside the masked
  element. Check on the lab page (`apps/ui/app/render/lab/factory/`) before building.
- `[data-iso-paused]` freezes a parcel's CSS run while the scene clock keeps going, so after a pause the parcel is
  behind the scene. Either re-key it on resume (it restarts at its true place) or accept the drift for a 2 s run.
- Frame cost with 40 parcels and 20 buddies under the extra motions: measure on the lab page, the way the label
  plate decision was measured.
