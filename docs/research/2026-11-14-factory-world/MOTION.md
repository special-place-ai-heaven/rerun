# Motion research: making the factory world move, deform and glow

As of 2026-11-14. Research only; nothing here is wired into the app. Target: the isometric
DOM/CSS world in `packages/ui/src/iso-grid` (see `styles.css`), where AI coworkers run, see-through
copies of a coworker work in parallel, and jobs travel between build, review, checks and merge.

## How to read this

- **Evidence label** on every find. *Derived from source* means I read the CSS/JS (or the repo
  manifest) and the motion is described from the code. *Caption only* means I read the page text,
  title or README and could **not** see the motion itself. I watched no video and ran no pen.
- **Licence**: public CodePen pens are MIT ("Public pens are automatically MIT licensed",
  https://blog.codepen.io/docs/licensing/). Blog and article code (CSS-Tricks, dev.to, Josh Comeau) has
  no stated licence, so it is paraphrased, not quoted.
- **Portability**: *CSS-portable* means it ports to the iso-grid as CSS keyframes. *Technique only*
  means it runs on a runtime we will not add (Three.js, PixiJS, GSAP, Rive, Lottie, canvas).
- **The recipes at the end are unrun.** They are written against the constraints `styles.css` already
  states, but no recipe has been tried in the app or timed in a browser.

## Constraints the world already sets (read from `styles.css`, not from docs)

1. A buddy moves **by its top only**: the top face translates by a share of `--buddy-depth` and the
   walls stretch by the same share (`iso-buddy-bob-top` / `iso-buddy-bob-wall`; top `-0.2` share pairs
   with wall `scaleY(1.2)`, top `+0.08` with `scaleY(0.92)`). The base never leaves its cells. So any
   whole-block `scale: x y z` squash from a pen does **not** transfer as written; it has to be
   re-expressed as this top/wall pair.
2. The flat-tile highlight layer animates **opacity only** (`iso-tile-halo`), because the wall layer
   carries a `mix-blend-mode` and a transform keyframe would isolate it from its backdrop.
3. Glow must not be per-frame `box-shadow`/`filter`/backdrop work: the label comment records that a
   backdrop blur under 150 names "cost three frames out of four". Fade a pre-painted glow layer.
4. Every loop must stop under `[data-iso-paused]` (CSS: `animation-play-state: paused !important` on
   all descendants) and under reduced motion (the `@media (prefers-reduced-motion: reduce)` list near
   line 818, plus `usePrefersReducedMotion` for inline tile animations). A loop driven from `motion`
   (`motion/react`, used in `TemplateCardBoard.tsx`, `useReducedMotion` in `hooks/useBoardOnHover.ts`)
   does **not** obey `[data-iso-paused]`; it has to be gated on the `paused` prop by hand.
5. Desynchronisation already uses `--buddy-delay` and prime-ish periods (bob 1.2 s, shudder 2.4 s,
   blink 4.6 s, glance 7.3 s). New loops should pick periods that do not divide these.
6. The cable comet already rides `offset-path` with `offset-rotate: auto` and a gradient tail, shown
   only under `@supports (offset-path: path('M0 0'))`, hidden under reduced motion.
7. The house ease-out is `cubic-bezier(0.22, 1, 0.36, 1)`; `agent-drop-in` encodes its ease in the
   spacing of the stops instead of the timing function.

8. The board already has a camera: the world wrapper carries `scale(zoom) translate(pan)` with a
   transition on `CAMERA_EASE`, which is the same house curve (`IsoGrid.tsx:1253`, constant at line 40).
9. The app already uses `linear()`: each cable's comet times its travel and its rest with two
   `linear()` easings set inline (`components/TileLinks.tsx:347`).

**Not to confuse:** `TileBuddy`'s `ghost` prop is the *placement draft* (muted or red while dragging a
new tile), not the parallel see-through copies. The copies exist in the factory scene as ordinary
buddy tiles with `opacity: 0.6` (`apps/ui/components/factory/factory-scene.ts:139`, `copy: true`);
`TileBlock.tsx:98` multiplies that into the block's opacity.

## Surfaces reached, and the ones that were not

| Surface | Result |
|---|---|
| CodePen | Reached. CodePen pages and `.css` endpoints return 403 / a bot check to both this PC and crawl4ai, but `https://cdpn.io/<user>/fullpage/<id>` returns the pen inside `srcdoc`; every CodePen find below is read from that. |
| GitHub | Reached (READMEs via crawl4ai, stars/licence/last push via the GitHub API, raw files). |
| Dribbble | **Not reached for motion.** crawl4ai got a challenge page; WebFetch got empty shot pages. Only a collection's titles came through (all flat workflow-builder dashboards, nothing that states motion). No Dribbble shot is ranked. |
| Behance | **Not reached** (crawl4ai 502). Search snippets only; none ranked. |
| Awwwards | Reached, thin: the "3D AI Agent Website" inspiration entry (MainLabs AI) has tags and no motion text. Not ranked. |
| Godly | `godly.website` now lands on `recent.design`; no agent-UI entries found. |
| Reddit | **Not reached**: the search JSON endpoint returned a redirect / non-JSON to this PC. Reddit-sourced claims below come from search-engine summaries and are flagged. |
| X.com | **Not reached**: not fetchable; no post could be confirmed. |
| Rive / Lottie | Reached as captions: Rive "Q Robot" (CC BY) and LottieFiles "AI Isometric" pack (45 files, licence not stated). Runtimes are technique only. |

So the ranked list leans on code (CodePen, GitHub) more than on design showcases. That is a gap
in the hunt, not a judgement that showcases have nothing; the showcase sites block automated reads.

## Ranked finds

Ranked by how much each would add to this world, weighted by how directly it ports to CSS.

### 1. jh3y, "Squish-squosh" 3D cuboid loader
https://codepen.io/jh3y/pen/wvEMOjJ · *derived from source* · MIT · CSS-portable (with re-expression)

**What moves:** a CSS cuboid squashes and stretches **in 3D**: `scale: 1.2 0.8 1.2` (squash: wider
on both floor axes, shorter) at 10% and 35%, `scale: 0.8 1.2 0.8` (stretch) at 25%. A `jump`
translates it `-150%` at 25%, so the stretch happens in the air and the squash on take-off and landing.
Its floor shadow runs the same keyframes and fades to `0.5` opacity at the peak. During the jump
(10% to 30%) it spins `-360deg`, and the whole `body` scales `1 -> 0.5` between 10% and 35%. Then,
while the body holds at 0.5, the cube doubles one axis at a time (70%, 80%, 90%) to `2 2 2`: at the
loop point 2 x 0.5 = 1, so the scene is back where it began. It is a seamless zoom loop, not just a
pull-back. Timeline 2.6 s, delay 0.65 s, all driven by `--timeline` / `--delay`.
**Why it reads as impressive:** it keeps volume (when height drops, both floor axes grow), and the
shadow and the camera move with the body, so it reads as weight in a space and not a sprite wobble.

```css
/* jh3y, CodePen wvEMOjJ, MIT (excerpt; the spin and the body scale are left out) */
@keyframes squish-squosh {
  0%, 50%, 60% { scale: 1 1 1; }
  10%, 35%     { scale: 1.2 0.8 1.2; }
  25%          { scale: 0.8 1.2 0.8; }
  70%          { scale: 1 1 2; }
  80%          { scale: 2 1 2; }
  90%, 100%    { scale: 2 2 2; }
}
@keyframes jump {
  0%, 10%, 35%, 50% { translate: 0 0; }
  25%               { translate: 0 -150%; }
}
@keyframes fade { 0%, 10%, 40%, 50%, 60%, 100% { opacity: 1; } 25% { opacity: 0.5; } }
```

### 2. steveeeie, "CSS 3D Convert-O-Matic"
https://codepen.io/steveeeie/pen/VyQXqK · *derived from source* · MIT · CSS-portable

**What moves:** a flat 2D robot rides a conveyor (`translate3D(-256px -> 0)` over the first half of a
4 s linear loop), disappears into a machine, and a **different, 3D** robot comes out the other side
(`0 -> 256px` over the second half). The machine bobs `translateZ(0 -> -20px)` 2 s linear alternate,
and each floor shadow scales `0.5 -> 1` with opacity `0.05 -> 0.1` on the same 2 s beat.
**Why:** it is exactly the factory story: a job goes into a station as one thing and comes out as
another. The trick is an element swap hidden inside the station, not a morph.

```css
/* steveeeie, CodePen VyQXqK, MIT (excerpt) */
.converter { animation: bob 2s infinite linear alternate; }
@keyframes bob { 0% { transform: translateZ(0); } 100% { transform: translateZ(-20px); } }
@keyframes bot2d { 0% { transform: translate3D(-256px,0,-8px); } 50%, 100% { transform: translate3D(0,0,-8px); } }
@keyframes bot3d { 0%, 50% { transform: rotateX(-90deg) translate3D(0,-30px,0); }
                   100% { transform: rotateX(-90deg) translate3D(256px,-30px,0); } }
@keyframes shadow { 0% { opacity: .05; transform: translateX(-50%) scale(.5); }
                    100% { opacity: .1; transform: translateX(-50%) scale(1); } }
```

### 3. thebabydino, "Pure CSS loader #18 - sliced cube"
https://codepen.io/thebabydino/pen/GRgYQge · *derived from source* · MIT · CSS-portable

**What moves:** a cube cut into 4 slices; each slice runs the same 8 s bounce with delay
`calc(var(--k)/var(--n)*4s - 8s)`. The **negative** delay means every slice is already mid-loop on
first paint, offset by a quarter phase, so the bounce ripples across the cube. Each bounce alternates
`ease-out` (rising) and `ease-in` (falling) **per keyframe**, with decaying heights
(2em, 1.99, 1.875, 1.367), and the shadow under each slice scales with a registered `@property --sr`.
**Why:** overlapping action and gravity from plain keyframes, no JS; the per-keyframe timing switch
is what makes the rebounds feel heavy.

```css
/* thebabydino, CodePen GRgYQge, MIT (excerpt) */
.slice { animation: a 8s calc(var(--k)/var(--n)*4s - 8s) infinite forwards; }
@keyframes cuboid {
  0%, 52.5%, 56.25%, 58.75%, 60%, 100% { transform: translatey(-2em); }
  2.5%, 6.25%, 8.75%, 10%, 50%          { transform: translatey(2em); }
  4.375% { transform: translatey(1.36719em); }  54.375% { transform: translatey(-1.36719em); }
  7.5%   { transform: translatey(1.875em); }    57.5%   { transform: translatey(-1.875em); }
  9.375% { transform: translatey(1.99219em); }  59.375% { transform: translatey(-1.99219em); }
  52.5%, 56.25%, 58.75%, 2.5%, 6.25%, 8.75% { animation-timing-function: ease-out; }
  54.375%, 57.5%, 59.375%, 4.375%, 7.5%, 9.375% { animation-timing-function: ease-in; }
}
```
(Rest at 2em; the rebound apexes are 0.63em, 0.125em and 0.008em above it: a fifth, then a
sixteenth, of the one before. The second half mirrors the first while the cube flips with `steps(1)` at 50%.)

### 4. Magic UI, Animated Beam and Border Beam
https://github.com/magicuidesign/magicui (`apps/www/registry/magicui/animated-beam.tsx`,
`border-beam.tsx`) · *derived from source* · MIT · 23.3k stars, last push 2026-11-13 (active) ·
uses `motion/react`, the same library Rerun has.

**What moves:** Animated Beam animates an SVG `linearGradient`'s `x1`/`x2` (`["10%","110%"]` /
`["0%","100%"]`, reversed for the other direction) along a curved path, `duration` 5 s, ease
`[0.16, 1, 0.3, 1]` (ease-out-expo, commented in the source), repeat infinite. The gradient is
transparent, then the start colour, the stop colour at 32.5%, then transparent, so a bright packet
with a soft tail runs the wire. Border Beam moves a small gradient blob round a box with
`offsetPath: rect(0 auto auto 0 round <size>px)` and `offsetDistance` 0 to 100%.
**Why:** ease-out-expo on a packet reads as "launched": fast leave, slow arrival. It is the
handoff gesture of most agent-workflow landing pages.
**Port note:** Rerun's comet is already the cheaper form (one element on `offset-path`). Take the
ease and the gradient stops, not the component. A `motion` loop ignores `[data-iso-paused]`.

### 5. Vibecraft (nearcyan)
https://github.com/nearcyan/vibecraft · *caption only* for motion, *derived* for stack · MIT ·
1.47k stars, last push 2026-01-18 (ten months: stalling) · Three.js (technique only)

**What moves (README):** an animated character works at **stations** by tool: a Terminal with a
glowing screen for shell commands, a Portal with a glowing ring for subagents; "mini-Claudes spawn at
portal for parallel tasks"; "celebrates commits, shakes head on errors"; thought bubbles while it
thinks; floating labels over active stations. A third-party write-up (starlog.pages.dev, see below)
adds that it walks to a bookshelf for reads and a desk for writes, with a sound per station.
**Why:** the closest published thing to Rerun's world: place means activity, and parallel copies
are born from a visible source instead of popping in.
**Doc/code gap:** a third-party write-up (starlog.pages.dev) says the avatar tweens with GreenSock;
Vibecraft's `package.json` lists `three`, `tone` and `ws`, and no GSAP. The write-up is wrong there.

### 6. jh3y, "Print.css but not how you know it: a 3D CSS printer"
https://dev.to/jh3y/printcss-but-not-how-you-know-it-creating-a-3d-css-printer-1o0k ·
*derived from article code* · licence not stated (paraphrased) · CSS-portable

**What moves:** a sheet flies from a paper stack into a CSS cuboid printer and a printed sheet comes
out. Two lessons in the code. First, the moving thing is split across wrappers: one element does the
travel, its child does the turn (an arc with `rotateY(-75deg)` that rises by 1.2 times the printer
height at its midpoint), and the feed into the slot starts after a delay computed with `calc()` from
the same speed property, so the chain stays in sync when the speed changes. Second, "the paper isn't
the same element throughout": one element goes in, another comes out.
**Why:** separate axes on separate wrappers is what gives overlap (the turn trails the travel), and
the swap is the same trick as find 2.

### 7. Alphardex, "3D Stair Loading"
https://codepen.io/alphardex/pen/YzqrGXb · *derived from source* · MIT · CSS-portable (idea)

**What moves:** seven isometric cuboids of rising height (3rem to 21rem) each collapse to height 0 at
50% of a 2 s loop and grow back, delays 0.2 s apart, `ease-in-out-cubic`; the height is a registered
custom property (`CSS.registerProperty('--cube-height')` in the pen's JS), so the faces resize with it.
**Why:** a staircase that breathes in sequence reads as flow along the row: a pipeline at rest still
shows its direction.
**Port note:** animating a length property resizes faces every frame (layout). In Rerun use the
top/wall transform pair and keep only the 0.2 s sequential stagger.

```css
/* alphardex, CodePen YzqrGXb, MIT (excerpt; --cube-height is registered as a length in the JS) */
.stair .cube { animation: bulge 2s infinite var(--ease-in-out-cubic); }
.stair .cube:nth-child(1) { --cube-height: 3rem; animation-delay: 0s; }
.stair .cube:nth-child(2) { --cube-height: 6rem; animation-delay: 0.2s; }
/* and so on: seven cubes, each 3rem taller and 0.2s later */
@keyframes bulge { 50% { --cube-height: 0; } }
```

### 8. claude-office (paulrobello)
https://github.com/paulrobello/claude-office · *caption only* (README) · MIT · 616 stars, last push
2026-11-11 (active) · Next.js + PixiJS (technique only)

**What moves (README):** a boss character spawns employee subagents who walk into the office; a
trash can fills with paper as the context window fills, and on compaction the boss stomps on it;
a printer animates when work produces a report; a day/night skyline; thought and speech bubbles.
**Why:** every animation is tied to a real event, and the gestures are funny. Each system event gets
one readable physical gesture, which is the bar for Rerun's jobs.

### 9. PixelFloor (fumeilab)
https://github.com/fumeilab/pixelfloor · *caption only* (README) · MIT · 0 stars, last push
2026-03-13 (no adoption: a reference, not a dependency) · canvas (technique only)

**What moves (README):** "data flow particles trace bezier curves between agents"; `sendParticle(from,
to)` fires one glowing particle per handoff; working agents "lean into their monitor" with a status
dot; celebrating agents jump with sparkles; error turns the dot red.
**Why:** one particle per real event is legible in a way a constant stream is not.

### 10. raykuo, "Pure CSS 3D isometric Wave animation"
https://codepen.io/raykuo/pen/ZEVZOgL · *derived from source* · MIT · CSS-portable

**What moves:** a grid of isometric boxes rises and falls in a wave: `translateZ` up to the box's
scaled height at 50%, 3 s, a delay of 0.1 s per step, timing `cubic-bezier(.74,.14,.18,.91)`
(slow start, fast middle, long soft landing).
**Why:** the curve is the find: it hangs at the bottom and at the top, which reads as mass.

```css
/* raykuo, CodePen ZEVZOgL, MIT (excerpt) */
.box {
  animation-name: wave;
  animation-delay: calc(var(--scale, 1) * var(--animation-delay)); /* --animation-delay: .1s */
  animation-duration: var(--animation-duration);                  /* 3s */
  animation-iteration-count: infinite;
  animation-timing-function: cubic-bezier(.74,.14,.18,.91);
}
@keyframes wave { 50% { transform: translateZ(calc(var(--scale, 1) * var(--box-height))); } }
```

### 11. whatsmyagentdoing (Charonyuu)
https://github.com/Charonyuu/whatsmyagentdoing (README via the everydev.ai listing) · *caption only*
· MIT · 401 stars, last push 2026-11-07 (active) · 2D canvas and 3D (technique only)

**What moves:** working agents at desks show a thought bubble while thinking, type while a tool runs,
and wave when they need the user; finished agents wander off duty (pantry, couch, arcade).
**Why:** a small, complete pose vocabulary per state, including "needs you", which is the state
most dashboards bury.

### 12. Onder Kadagan, "Analysis Center: Isometric Motion Design in Rive"
https://contra.com/p/3sklmLUB-analysis-center-isometric-motion-design-in-rive · *caption only*
(video not watched) · licence not stated · Rive (technique only)

**What moves (caption):** an isometric hub collects data from four areas through "animated data
lines", with timing, easing and depth tuned to hold the isometric perspective. **Why it is here:**
the only showcase piece found that is isometric, about flowing work, and states its motion.

### 13. Josh Comeau, "Springs and Bounces in Native CSS" (with Chrome's guide to `linear()`)
https://www.joshwcomeau.com/animation/linear-timing-function/ and
https://developer.chrome.com/docs/css-ui/css-linear-easing-function · *derived from article* ·
licence not stated (paraphrased; the values in recipe 9 are generated by me)

**What it gives:** `linear()` takes a list of progress points (values above 1 overshoot), so a real
spring can be sampled into CSS. His pattern: a custom property holds a `cubic-bezier` fallback and is
overwritten with the `linear()` spring inside `@supports (animation-timing-function: linear(0, 1))`,
with the stiffness and damping noted in a comment so it can be retuned.
**Why:** springs with no library, and as CSS they still stop under `[data-iso-paused]`.

### 14. Pixel Agents (pablodelucca)
https://github.com/pablodelucca/pixel-agents · *caption only* (search summaries; the repo has moved
and the API redirected) · code licence not confirmed; its default tileset is paid and not in the repo

**What moves (summaries):** coding agents become pixel characters in an office; Task sub-agents spawn
as separate characters linked to their parent. **Why it is here:** the most-shared example of the
genre; the visible parent link is the idea to borrow for see-through copies.

### 15. "AI Agent Animation", a Framer component (Iklil Najma Muqtafa)
https://www.framer.com/marketplace/components/ai-agent-animation/ · *caption only* · paid ($15),
published 2026-11-04 · no code available

**What moves (listing):** up to 8 coloured worker agents with "smooth cursor movements and live status
badges" build a page step by step with "draft-and-drop" moves and typewriter text. **Why it is here:**
the newest piece found (ten days old), and it shows the current fashion: many visible workers
assembling one artefact. Nothing to port.

Also read, not ranked: Brandon Gregory, "Making CSS Animations Feel Natural" (CSS-Tricks, 2018:
a squash before the jump, a second small rebound with its own squash, a pause between jumps;
recipe 1 uses it); Agustin Capeletto, "CSS Meets Voxel Art" (Codrops: stacked CSS grids as an
addressable 3D space; a build technique, not motion); pyxofy, "Isometric Cubes with Move and Text
Glow" (animates `top`, which is layout every frame: skip); Rive "Q Robot" by JcToon
(https://rive.app/community/4494-9153-q-robot, CC BY, caption only: a boned robot whose state machine
moves it to a new spot on each button press, even mid-move; Rive runtime, technique only).

## Ten motion recipes for the iso-grid

All unrun. Each names its source find. Notation for buddies, matching the existing bob: a top
share `s` means the top layer gets `translateY(calc(var(--buddy-depth) * <s>px))` and the wall layer
gets `scaleY(1 - s)`; negative `s` lifts the top. So "share -0.32" is top `-0.32`, wall `1.32`.
Every recipe is CSS keyframes, so `[data-iso-paused]` freezes it for free; each new class also has
to join the `prefers-reduced-motion` list in `styles.css`.

**One-shots and loops share layers.** The top and wall layers already run a looping `transform`
animation chosen by `[data-buddy-motion]`. Two animations on one layer that both set `transform` do
not add up: the later one in the list wins. So a one-shot (R1, R5's shudder, R6, R7's catch) swaps
the motion value for its duration and hands back when its last stop is at share 0, where every loop
also starts.

### R1. Hop of a coworker taking a job (anticipation, stretch, squash, settle)
Sources: find 1 (volume and shadow move together), find 3 (ease-out rising, ease-in falling, per
keyframe), CSS-Tricks "feel natural" (squash before the jump, small second rebound).
One-shot, 900 ms, on the event "job picked up". The base stays on its cells; the top does the hop.

| stop | top share | wall | pool (scale, opacity) | timing from this stop |
|---|---|---|---|---|
| 0% | 0 | 1 | 1, 1 | `ease-in-out` |
| 14% (crouch) | +0.12 | 0.88 | 1.04, 1 | `cubic-bezier(0.2, 0.7, 0.3, 1)` (launch) |
| 38% (stretch) | -0.32 | 1.32 | 0.86, 0.55 | `cubic-bezier(0.32, 0, 0.67, 0)` (falls in) |
| 58% (landing squash) | +0.10 | 0.90 | 1.06, 1 | `ease-out` |
| 72% | -0.03 | 1.03 | 1, 1 | `ease-in-out` |
| 84% | +0.01 | 0.99 | 1, 1 | `ease-out` |
| 100% | 0 | 1 | 1, 1 | |

Find 1 also widens on the squash; the base here cannot widen. An optional, untested cheat is a
`scale(1.04)` on the top face only at 58%.

### R2. Landing with decaying rebounds (a job or a new coworker arrives)
Sources: find 3 (each rebound is a fifth, then a sixteenth, of the one before; ease alternates per stop), find 2
(the shadow grows as the thing nears the floor), the existing `agent-drop-in`.
1100 ms, one-shot, `translateY` on the arriving thing; the paired top/wall squash only for buddies.

```css
@keyframes iso-land-rebound {
  0%  { transform: translateY(-100px); opacity: 0; animation-timing-function: cubic-bezier(0.5, 0, 0.75, 0); }
  12% { opacity: 1; }
  45% { transform: translateY(0); animation-timing-function: cubic-bezier(0.25, 1, 0.5, 1); }
  60% { transform: translateY(-14px); animation-timing-function: cubic-bezier(0.5, 0, 0.75, 0); }
  72% { transform: translateY(0); animation-timing-function: cubic-bezier(0.25, 1, 0.5, 1); }
  80% { transform: translateY(-3px); animation-timing-function: cubic-bezier(0.5, 0, 0.75, 0); }
  86%, 100% { transform: translateY(0); }
}
/* buddies only, same duration: contact squash at 45% (share +0.12), 72% (+0.05), 86% (+0.02),
   back to 0 within 6% after each contact. Pool: scale 0.6 / opacity 0.3 at 0%, 1 at 45%, 0.9 at 60%. */
```
The fall is kept separate from the blur and opacity of `agent-drop-in`; whether to merge them is a
taste call.

### R3. See-through copies that ripple from their coworker (overlap, follow-through)
Sources: find 3 (negative staggered delays), find 5 (copies born at a visible source), find 14
(copies linked to their parent), find 6 (secondary parts trail the main one).

- Each copy is the same buddy at about `opacity: 0.4`, index `--k` of `--n` copies, running the
  parent's bob with `--buddy-delay: calc(var(--k) / (var(--n) + 1) * -1.2s)` for `k` = 1 to `n`
  (dividing by `n + 1` keeps the last copy off the parent's phase; `k / n` would put copy `n` one full
  period back, in step with the parent). The negative delay puts every
  copy mid-loop from the first frame, so the bob runs as a wave outward from the parent instead of a
  row of identical clones bouncing together.
- Follow-through: the copy's label and pool use the same keyframes with 60 ms more delay than its
  body, so they settle a beat after it.
- Birth: each copy starts at the parent's position and travels to its own cells with the spring of
  R9, 120 ms apart per copy, opacity 0 to 0.4. Death runs it backwards into the parent.
- Parent link: a thin cable from the parent to each copy (the existing cable and comet already exist).
- **Risk (unchecked):** `opacity < 1` on a group isolates its children, and the pool uses
  `mix-blend-mode`. Check whether the block opacity at `TileBlock.tsx:98` wraps the pool; if it does,
  a copy's pool stops blending with the floor. Render it outside the translucent group, or accept it.

### R4. Shadow that follows height (depth)
Sources: find 2 (shadow scale 0.5 to 1 and opacity 0.05 to 0.1 on the bob's beat), find 1
(shadow shares the squash and fades at the peak), find 3 (one shadow per slice).
Rule for every new lift, with `lift` from 0 (on the floor) to 1 (its highest point): pool
`scale(1 - 0.5 * lift)`, `opacity: 1 - 0.8 * lift`, written at the **same keyframe stops and timing
functions** as the lift, never a separate easing, or the shadow slides out of phase. For a job lifted
while it travels along a cable, put its shadow on a second element on the same `offset-path` with
`offset-rotate: 0deg`, so the shadow stays on the floor while the job rides above it.

### R5. Station swap: a job goes in as one thing and comes out as another
Sources: find 2 (conveyor in at constant speed, a different robot out), find 6 (the sheet that goes
in is not the sheet that comes out), the existing `iso-buddy-shudder-*` and `iso-tile-halo`.
2250 ms in four beats:
1. 0-900 ms: the incoming token rides the cable into the station, `offset-distance` 0 to 100%,
   `linear` (a belt moves at constant speed; both conveyor pens are linear).
2. At the door: the token fades out in 80 ms.
3. 900-1350 ms: the station shudders once (the shudder keyframes, one iteration) while its
   pre-painted glow layer goes opacity 0.4 to 1 to 0.4.
4. 1350-2250 ms: a **new** token (the next state's colour or badge) fades in at the out door in
   80 ms and rides out, `linear`.
No morph, no layout: two elements, two paths, one hidden swap.

### R6. The pipeline breathes in order at rest (stagger and glow)
Sources: find 7 (sequential 0.2 s stagger along a row), find 10 (the curve that hangs at both
ends), the existing `iso-tile-halo` (opacity-only glow).
Build, review, checks and merge each get `--station-index` 0 to 3. Period 2.9 s, which does not
divide the existing 1.2, 2.4, 4.6 or 7.3 s, so it never locks to the bob or the blink.

Stations in the factory scene are rooms with coworker buddies in them, so the breathe goes on each
room's lead buddy (top/wall pair). If it goes on a room's flat floor container instead, keep only the
opacity glow (constraint 2).

```css
@keyframes iso-station-breathe-top {
  0%, 40%, 100% { transform: translateY(0); }
  14% { transform: translateY(calc(var(--buddy-depth) * -0.08px)); }
  26% { transform: translateY(calc(var(--buddy-depth) * 0.02px)); }
}
@keyframes iso-station-breathe-wall {
  0%, 40%, 100% { transform: scaleY(1); }
  14% { transform: scaleY(1.08); }
  26% { transform: scaleY(0.98); }
}
@keyframes iso-station-glow { 0%, 40%, 100% { opacity: 0.35; } 14% { opacity: 0.9; } }
/* --breathe-ease: cubic-bezier(0.74, 0.14, 0.18, 0.91); --breathe-delay: calc(var(--station-index) * 0.2s) */
[data-buddy-motion='breathe'] .iso-buddy-top  { animation: iso-station-breathe-top 2.9s var(--breathe-ease) var(--breathe-delay) infinite; }
[data-buddy-motion='breathe'] .iso-buddy-wall { animation: iso-station-breathe-wall 2.9s var(--breathe-ease) var(--breathe-delay) infinite; }
[data-buddy-motion='breathe'] .iso-station-glow { animation: iso-station-glow 2.9s var(--breathe-ease) var(--breathe-delay) infinite; }
```
(`.iso-buddy-top` and `.iso-buddy-wall` are the classes the bob rules already target; `.iso-station-glow`
is a new, pre-painted glow layer.)

The pulse runs build to merge, so the direction of work is visible before any job moves.

### R7. Handoff comet: launched fast, arrives soft, the receiver catches it (particles, glow)
Sources: find 4 (ease-out-expo packet, gradient stops transparent to colour to transparent),
find 9 (one particle per real handoff), the existing `iso-cable-comet` and `agent-ping`.
- Fire one comet per real handoff event, not a constant stream. Make it a **separate one-shot
  element** on the cable's path, not a change to the looping comet: that comet runs two animations
  (travel and rest) whose two inline `linear()` easings set each cable's travel/rest split, so one
  new timing function would break its rest. The one-shot: `offset-distance` 0 to 100%,
  `cubic-bezier(0.16, 1, 0.3, 1)`, 900 ms, one iteration, removed on `animationend`.
- With that curve the comet has covered most of the cable by about half its time, so start the
  receiver's reaction at 450 ms: the existing `agent-ping` ring (scale 1 to 1.6, fading by 70%) and a
  160 ms top-only "catch" (share +0.06, back to 0).
- Glow head: a second, pre-blurred copy of the head riding the same path. Its `filter` is set once
  and never animated; only its transform moves. Whether a static blur on a moving layer stays cheap
  with many cables at once is unmeasured.

### R8. A short particle trail on a busy cable
Sources: find 9 (particles along the path between agents), the existing comet; staggering several
dots on one `offset-path` is a technique from a search summary, not a pen I read.
Three one-shot elements (as in R7, not the looping comet) on the same path and timing, delays 0, 70 and 140 ms, `scale` 1, 0.7 and 0.45,
opacity 1, 0.55 and 0.3. Only on cables carrying a handoff right now, so the element count is bounded
by live handoffs, not by the number of cables.

### R9. Spring settle for two-state moves (copy spawn, job landing in a slot, label pop)
Sources: find 13 (`linear()` springs with an `@supports` fallback). The values are mine, sampled
from a damped spring x(t) = 1 - e^(-z w t) (cos(w_d t) + (z w / w_d) sin(w_d t)), w = sqrt(k),
z = c / (2w), with k 180, c 12, mass 1, at 41 even points over 5 / (z w) seconds. The board already
uses `linear()` (constraint 9), so the `@supports` fallback is belt and braces.

```css
:root {
  --iso-spring: cubic-bezier(0.34, 1.56, 0.64, 1); /* fallback: an ease-out-back */
  --iso-spring-time: 830ms;
}
@supports (animation-timing-function: linear(0, 1)) {
  :root {
    /* stiffness 180, damping 12, mass 1: settles in about 830 ms, overshoots 21% */
    --iso-spring: linear(0, 0.036, 0.13, 0.263, 0.417, 0.577, 0.731, 0.869, 0.986, 1.078, 1.144,
      1.185, 1.205, 1.206, 1.193, 1.17, 1.14, 1.107, 1.074, 1.043, 1.016, 0.994, 0.977, 0.966,
      0.959, 0.957, 0.958, 0.962, 0.967, 0.974, 0.981, 0.988, 0.994, 0.999, 1.003, 1.006, 1.008,
      1.009, 1.009, 1.008, 1);
  }
}
```
Use it only on a `from`/`to` keyframe or a transition. A timing function applies per segment, so on a
multi-stop keyframe the overshoot would repeat at every stop.

### R10. Camera: a dolly toward the action, and a slow drift
Sources: find 1 (the whole scene scales with the action, and the zoom loops seamlessly because
the subject grows as the camera pulls back), find 5 (the view follows the active station), the
existing camera (constraint 8).
- Focus: no new wrapper. Drive the camera the board already has: when a station is selected or a job
  lands in merge, raise `zoom` about 6% and move `pan` toward that station's centre with `animating`
  on, 1200 ms on `CAMERA_EASE`; back out in 800 ms.
- Idle drift, optional: an extra inner wrapper `scale(1)` to `scale(1.012)`, 23 s `ease-in-out`
  alternate (23 is co-prime with every period here), so the world never sits perfectly still. It must
  not fight the pan/zoom transform, so it goes on its own element.
- Never on layers that carry a blend mode. Under reduced motion: no drift, and focus becomes a cut.

## Periods in use, so new loops stay out of step

Existing: bob 1.2 s, shudder 2.4 s, comet per cable, blink 4.6 s, glance 7.3 s, beam 4 s, placeholder
shine 7 s. Proposed: station breathe 2.9 s, camera drift 23 s. Everything else above is a one-shot
fired by an event.

## Where to start

1. R7 and R5 first: they turn real events (handoff, station work) into visible gestures, and they
   reuse the comet, the ping and the shudder that already exist.
2. R1 and R3 next: they make the coworkers and their see-through copies feel alive.
3. R9 is a token (`--iso-spring`) that R3 and R5 share; add it with the first of them.
4. R10 last, and only after measuring frame time with many buddies on screen.

Before any of these ships: try one in a branch, record frame time with about 150 buddies on the
board, and check `[data-iso-paused]` and reduced motion by hand.
