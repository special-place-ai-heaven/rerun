# A 3D factory world: references, stack and techniques
as_of 2026-11-14

Research only, nothing built. The question: which real, open 3D browser scenes of agents (or software work)
are worth learning from for a Rerun factory view, and what stack and techniques would get the board's
rounded, faced buddies into a true 3D world. Kanban boards, node editors and chat panels were out of scope.

How it was done: code first. Each reference below was read in its source on GitHub (`gh api`); where a
description leans on a README or screenshot it says so. Seven were also looked at as pictures (README
screenshot or demo frame). Sizes come from a
local esbuild probe, not from bundlephobia. Licences were read in each repository's LICENSE file.

Not reached: Reddit (its search answered 403 to a script), X.com posts (search returned only articles about
them), Awwwards and the Spline community (no open source to read there), Codrops (one search, nothing on
topic). Hacker News was searched through its public API: the best-received agent office was "Outworked"
(48 and 44 points, March 2026), and it is 2D (Phaser, GPL-3.0); no 3D agent office found had a thread above a
few points, and one review of Claw3D notes that some readers call the genre a gimmick. Take that as the
field's state: there is no 3D hit yet, so the bar is quality, not novelty.

## 1. What Rerun has today (from the code)

- No 3D library anywhere: `pnpm-lock.yaml` has zero lines matching `three`, `react-three`, `babylon`,
  `playcanvas` or `spline`, and `node_modules/three` / `node_modules/@react-three` do not exist.
- Web app: `apps/ui/package.json` has `next` 16.4.6, `react` 19.3.1, `motion` ^12.43.0. Repo licence AGPL-3.0.
- The board is DOM/SVG/CSS in `packages/ui/src/iso-grid`. The grid is 2:1 dimetric (`iso.ts`: `TILE_W = 56`,
  `TILE_H = 28`), not true isometric.
- A buddy (`components/buddy/RoundedBox.tsx`, `BuddyFace.tsx`, `buddy-look.ts`) is a rounded block on a 2x2
  footprint (`BUDDY_FOOTPRINT_SHARE = 0.8`); the face is SVG drawn in the front-left wall's plane (17 eye
  styles, 5 mouths). Body colour by mood: amber `#f59e0b` working, red `#ef4444` error, cyan `#06b6d4`
  waiting, theme grey idle and asleep; a resting top takes one of 8 identity colours.
- Motion (`styles.css` lines 204-320): the base stays on its cells and only the top moves. Bob: walls
  `scaleY` 1 -> 1.2 (35%) -> 0.92 (62%) -> 1.02 (78%) -> 1 over 1.2 s, `cubic-bezier(0.3, 0, 0.3, 1)`.
  Shudder: 0.9 / 1.06 / 0.95 / 1.02 between 60% and 84% of 2.4 s. Blink: eyes `scaleY(0.08)` at 95% of 4.6 s.
  Glance: pupils drift on a 7.3 s period. A light pool on the floor dims as the top rises. All of it stops
  under `prefers-reduced-motion`.
- `motion` cannot drive a 3D scene: its 3D package `framer-motion-3d` is deprecated on npm ("Package no longer
  supported"). Animation in 3D runs in the render loop (`useFrame`) with damping, or with `@react-spring/three`.

## 2. Ranked references

Ranked by how close each is to "a 3D software factory of rounded workers, jobs travelling between stations",
then by how good it looks. Stars are context, not rank. Health is as of 2026-11-14.

| # | Reference | Licence | Health | Look |
|---|---|---|---|---|
| 1 | [suleyman/3dokploy](https://github.com/suleyman/3dokploy) | MIT, "3Dokploy contributors" | created 2026-10-16, pushed 2026-11-11, 21 commits, 2 contributors, 28 stars; young, rising | neon iso city of server racks on a dark grid; carts drive deploys to racks; light beams; bloom |
| 2 | [brunosimon/folio-2025](https://github.com/brunosimon/folio-2025) | MIT, Bruno Simon | pushed 2026-11-04, 2,028 stars; stable | best art direction found: warm low-poly world, glowing lanterns, wind, soft bloom |
| 3 | [iamlukethedev/Claw3D](https://github.com/iamlukethedev/Claw3D) | MIT, Luke The Dev | pushed 2026-11-04, 2,459 stars; most adopted in the genre, rising | voxel office, orthographic, small people at desks; plain look, rich behaviour |
| 4 | [nearcyan/vibecraft](https://github.com/nearcyan/vibecraft) | MIT, nearcyan | 5 commits, pushed 2026-01-18, 1,471 stars; dormant | hex zones, one per running Claude instance, each with tool stations; dark, readable |
| 5 | [Charonyuu/whatsmyagentdoing](https://github.com/Charonyuu/whatsmyagentdoing) | MIT, cheoyu (code); Kenney CC0 models | pushed 2026-11-07, 401 stars; rising | bright orthographic office, rigged Kenney characters, status tags |
| 6 | [Khalidabdi1/factory](https://github.com/Khalidabdi1/factory) ("Factory Yard") | MIT, Khalid Abdi | pushed 2026-10-11, 161 stars; stable | hairline-drawn dark iso town; goods go factory -> warehouse -> shop; a clicked vehicle shows its route |
| 7 | [arturitu/the-delegation](https://github.com/arturitu/the-delegation) | code MIT; **3D assets CC BY-NC 4.0** | pushed 2026-04-16, 731 stars; stalling | cutest characters found (soft rounded figures, big eyes); the page around them is a kanban |
| 8 | [pmndrs/examples](https://github.com/pmndrs/examples) | MIT, Poimandres | pushed 2026-10-22; the reference set for r3f | `tilt-shift`, `confetti`, `springy-boxes`, `backdrop-and-cables`, `selective-bloom` |
| 9 | [Gaurav2693/ai-office](https://github.com/Gaurav2693/ai-office) | MIT, Gaurav Mishra | pushed 2026-03-31, 69 stars; stalling | small office, 9 agents; monitor screens are live canvas drawings |
| 10 | [ektogamat/threejs-holographic-material](https://github.com/ektogamat/threejs-holographic-material) | MIT, Anderson Mancini dos Santos | pushed 2024-03-25, 256 stars; finished, unmaintained | see-through hologram: fresnel edge, scanlines, flicker |

### 2.1 3dokploy: the nearest match, and the one to start from
- What moves: a deploy spawns a cart (a `RoundedBox` chassis with an emissive screen) that grows in over
  0.35 s, follows a route to its rack, docks, waits for the end state, drives back and shrinks out. A rack that
  is deploying gets an additive light column with travelling bands, a bright core line and a spinning floor
  ring; a finished deploy fires a one-off shockwave, green or red. A technician walks to racks in error. All
  motion runs on refs in `useFrame`; the store only hears "cart gone". Every effect checks `reducedMotion`.
- How: `<Canvas orthographic dpr={[1, 2]} shadows="percentage">`; environment light made of three
  `<Lightformer>` panels (nothing fetched); `<EffectComposer multisampling={4}>` with
  `<Bloom mipmapBlur luminanceThreshold={0.9} />`; glowing parts set `toneMapped={false}` so only they bloom.
- Stack: `three` ^0.186.1, `@react-three/fiber` ^9.8.2, `@react-three/drei` ^10.7.9,
  `@react-three/postprocessing` ^3.2.0, `react` ^19.3.1. These are the versions Rerun would install.
- Files: `src/scene/Agents.tsx` (carts, `Walker` path follower, `dampAngle`), `src/scene/Effects.tsx` (beams,
  shockwaves), `src/scene/Scene.tsx` (canvas, camera fit, lights, composer).
- Against: a month old, two contributors; the palette is neon, not Rerun's soft blocks. Take the structure.

Snippet, MIT, Copyright (c) 2026 3Dokploy contributors, `src/scene/Agents.tsx` lines 113-148 (condensed):
```tsx
useFrame((_, rawDt) => {
  const st = sim.current, g = group.current
  if (!g || !st.walker || st.phase === 'gone') return
  const dt = Math.min(rawDt, 0.1)
  st.age += dt
  let moving = false
  if (st.phase === 'out') {
    moving = true
    if (st.walker.step(CART_SPEED * dt)) { st.phase = 'docked'; setPhase('docked') }
  } else if (st.phase === 'docked') {
    st.docked += dt
    if (terminalRef.current && st.docked > 0.8 && route) {
      st.phase = 'back'; st.walker = new Walker(route.slice().reverse()); setPhase('back')
    }
  } else if (st.walker.step(CART_SPEED * dt)) {
    st.phase = 'gone'; useStore.getState().cartGone(deploymentId); return
  } else moving = true
  g.position.copy(st.walker.pos)
  const heading = st.phase === 'docked' ? FACE_RACK : st.walker.heading
  g.rotation.y = st.age < 0.05 ? heading : dampAngle(g.rotation.y, heading, 12, dt)
  const appear = Math.min(1, st.age / 0.35)
  const vanish = st.phase === 'back' ? Math.min(1, st.walker.remaining / 0.9) : 1
  g.scale.setScalar(Math.max(0.001, Math.min(appear, vanish)))
  if (chassis.current) chassis.current.position.y = moving && !still ? Math.abs(Math.sin(st.age * 16)) * 0.02 : 0
})
```

Beam shader, same licence and holder, `src/scene/Effects.tsx` (used with `AdditiveBlending`, `depthWrite: false`):
```glsl
uniform vec3 color; uniform float time; varying float vH;  // vH: 0 at the floor, 1 at the top
void main() {
  float fade = pow(1.0 - clamp(vH, 0.0, 1.0), 1.7);
  float bands = 0.6 + 0.4 * sin(time * 7.0 - vH * 26.0);
  gl_FragColor = vec4(color * 2.2, fade * bands * 0.5);
}
```

### 2.2 folio-2025 (Bruno Simon): the bar for "alive"
- What moves: a drivable toy car in a low-poly world; grass and wind lines sway, lanterns glow, a day cycle
  changes the light, objects explode and settle under physics (`@dimforge/rapier3d`).
- How: plain three.js 0.187 on `three/webgpu` (`WebGPURenderer`) with TSL nodes; bloom is the TSL `BloomNode`
  with threshold 1 and strength 0.25 (`sources/Game/Rendering.js` lines 78-98): only materials pushed above 1
  glow, and only a little. A cheap depth-of-field pass, instanced groups (`InstancedGroup.js`), one shared
  default material (`Materials/MeshDefaultMaterial.js`).
- Fit: an idea source, not a code source. Its post chain is WebGPU-only; pmndrs `postprocessing` 6.x (what
  r3f uses) documents only `WebGLRenderer`. Borrow the restraint: low bloom strength, a high threshold, warm
  light, motion everywhere at low amplitude.

### 2.3 Claw3D: the most adopted agent office, and its face code
- What moves: people walk between rooms (lerped position, damped heading), sit, type, work out, dance; eyes
  blink on a per-agent seed; the mouth changes by state; an error ring pulses; a speech bubble pulses.
- How: `<Canvas orthographic dpr={[0.85, 1.5]} shadows={{ type: PCFShadowMap }}>`, `<Environment preset="city">`,
  `OrbitControls`; walls through `InstancedMesh`. No post-processing.
- Same stack as Rerun (`next` 16.1.7, `react` 19.2.3, `@react-three/fiber` ^9.5.0, `drei` ^10.7.7, `three`
  ^0.183.2). Files: `src/features/retro-office/objects/agents.tsx`, `systems/cameraLighting.tsx`,
  `RetroOffice3D.tsx` (273 KB in one file: read it, do not copy its structure).
- Two cautions from the code: animation counts frames (`agent.frame * 0.22`), so speed follows the screen's
  refresh rate; use `delta` instead. `Environment preset="city"` loads an HDR file from a CDN at run time
  (`useEnvironment.js` builds the URL from `https://raw.githack.com/pmndrs/drei-assets/...`); use `<Lightformer>` panels or three's `RoomEnvironment` instead.

Snippet, MIT, Copyright (c) 2026 Luke The Dev, `src/features/retro-office/objects/agents.tsx` lines 372-401
(condensed: eye scale constants inlined, the y offset left out):
```tsx
const blinkSeed = agentId.split('').reduce((sum, char) => sum + char.charCodeAt(0), 0)
const blinkCycle = isAway ? 180 : isError ? 120 : working ? 170 : 240
const blinkWindow = isAway ? 26 : isError ? 18 : 12
const blinkPhase = (agent.frame + blinkSeed * 17) % blinkCycle
let eyeOpen = isError ? 0.92 : working ? 0.84 : 1.12
if (blinkPhase < blinkWindow) {
  const midpoint = blinkWindow / 2
  eyeOpen *= Math.min(1, Math.abs(blinkPhase - midpoint) / midpoint)
}
if (working) eyeOpen = Math.max(0.48, eyeOpen)
if (isError) eyeOpen = Math.max(0.28, eyeOpen)
if (isAway) eyeOpen = Math.min(eyeOpen, 0.2)
for (const eyeRef of [leftEyeRef, rightEyeRef]) {
  if (!eyeRef.current) continue
  eyeRef.current.scale.x = isError ? 1.2 : working ? 1.06 : 1.12
  eyeRef.current.scale.y = Math.max(0.05, eyeOpen)
}
```

### 2.4 Vibecraft: parallel instances as places, tools as stations
- What moves: each running Claude session is a coloured hex zone; inside it a little character walks to the
  station of the tool it is using (read, edit, bash, search...) and plays a per-station loop
  (`src/entities/animations/WorkingBehaviors.ts`: hammering, typing, writing, with eased arm swings and eye
  drift); a station pulses when used (`stationPulses` in `src/scene/WorkshopScene.ts`).
- How: plain three.js 0.170, `PerspectiveCamera` over a hex grid (`src/utils/HexGrid.ts`). No post chain.
- Fit: the closest idea to "one main coworker with copies running in parallel": one zone per copy, same
  layout in each, so the eye compares them. Dormant since January; read it, do not depend on it.

### 2.5 whatsmyagentdoing: rigged characters without an artist
- How (`web/office3d.js`): orthographic camera, `PCFSoftShadowMap`, ACES tone mapping; Kenney CC0 characters
  loaded as glTF, cloned per agent with `SkeletonUtils.clone`, each with its own `AnimationMixer`; desk
  screens are emissive meshes whose colour and pulse follow the agent's state (thinking, tool, typing,
  waiting, error); name tags and bubbles are drawn by the 2D code on a canvas over the 3D view.
- Fit: proof that skinned idle/walk loops are cheap with CC0 assets. Rerun's buddies are blocks, not people,
  so the takeaway is the state-to-emissive mapping and the overlay for text, not the characters.

### 2.6 Factory Yard: things travelling on routes, and showing the route
- What moves: trucks carry goods factory -> warehouse -> shop; buses, a metro, ships, a day cycle with
  windows lighting at dusk, weather. Clicking a vehicle draws its whole route dashed on the ground and marks
  its next stop; a side card shows live details.
- How: plain three.js 0.186.1 in Next.js 16.3.8, `OrthographicCamera` (`yard/view.ts` line 30), a pure
  simulation folder (`yard/sim/*`, 28 files; the goods route is in `trucks.ts` and `freight.ts`) apart from
  the drawing (`yard/world/*`). The motion described above comes from the README and its screenshot; only the
  camera, the folder split and the file names were checked in code.
- Fit: the model for "a job is an object on a route": simulation separate from drawing, the selected job's
  path drawn dashed ahead of it.

### 2.7 The Delegation: the character charm, under a licence that rules the models out
- Soft, rounded figures with big eyes, the closest in spirit to Rerun's buddies. Under the hood: skinned
  animations baked into a GPU storage buffer and played on instanced meshes by a TSL compute pass
  (`src/simulation/entities/CharacterManager.ts`): WebGPU-only, more than Rerun needs.
- The models are CC BY-NC 4.0: not usable in a product that may be sold. Look, do not take.

### 2.8 pmndrs examples: the technique library (MIT, Copyright (c) 2024 Poimandres)
- `tilt-shift`: a toy-town look from `<TiltShift2 blur taper start end />`, with a narrow perspective camera
  (`fov: 30`) and an orthographic shadow camera.
- `confetti`: glowing ribbons, `meshline` with a dash pattern whose offset scrolls each frame, colours above 1
  (`[10, 0.5, 2]`) so bloom picks them up.
- `springy-boxes`: `useSprings` from `@react-spring/three` moving 35 boxes with mass/tension/friction.
- `backdrop-and-cables`: a cable that stays attached to two moving objects (`QuadraticBezierLine.setPoints`).
- `selective-bloom`: bloom on chosen objects only.

Snippet, `examples/confetti/src/App.tsx` (MIT, Poimandres): the scrolling glowing dash, the same idea as the
board's cable comets.
```tsx
function Fatline({ curve, width, color, speed, dash }) {
  const ref = useRef(null!)
  useFrame((state, delta) => (ref.current.material.dashOffset -= (delta * speed) / 10))
  return (
    <mesh ref={ref}>
      <meshLineGeometry points={curve} />
      <meshLineMaterial transparent lineWidth={width} color={color} depthWrite={false}
        dashArray={0.25} dashRatio={dash} toneMapped={false} />
    </mesh>
  )
}
```

Snippet, `examples/backdrop-and-cables/src/App.tsx` (MIT, Poimandres): a cable between two moving things.
```tsx
function Cable({ start, end, v1 = new THREE.Vector3(), v2 = new THREE.Vector3(), mid = new THREE.Vector3() }) {
  const ref = useRef(null!)
  useFrame(() => {
    const from = start.current.getWorldPosition(v1)
    const to = end.current.getWorldPosition(v2)
    ref.current.setPoints(from, to, mid.set(to.x, from.y, to.z))
  }, 0)
  return <QuadraticBezierLine ref={ref} start={[0, 0, 0]} end={[0, 0, 0]} lineWidth={3} color="#ff2060" />
}
```

### 2.9 ai-office: live screens
- Monitors are `CanvasTexture`s redrawn each frame with bars, waves and a blinking cursor in the agent's colour
  (`src/scene/OfficeScene.js` lines 960-995). A cheap way to give a station a working screen.
- Doc/code gap: the README calls it "isometric"; the code uses `PerspectiveCamera(30, ...)` (line 31) with an
  orbit rig, so it is a narrow-angle perspective, not an orthographic view.

### 2.10 Holographic material: the see-through copies
- An r3f material with a fresnel rim, scrolling scanlines and an optional flicker, colour and opacity as props
  (`src/HolographicMaterial.js`). A copy of the main coworker drawn with it reads as "the same one, again,
  not solid". Unmaintained since 2024, but it is one drei `shaderMaterial` (223 lines, read in full): vendor
  it, or write the fresnel yourself. One adjustment: its fresnel takes the view direction from
  `cameraPosition - vPositionW`; under an orthographic camera every view ray is parallel, so pass the
  camera's forward vector instead or the rim drifts across a wide scene.

### 2.11 More snippets (all read in the files named)

folio-2025, MIT, Copyright (c) 2025 Bruno Simon, `sources/Game/Rendering.js` lines 76-85. WebGPU/TSL only:
an idea for the numbers (threshold 1, strength 0.25), not portable code for r3f's WebGL composer.
```js
this.postProcessing = new THREE.RenderPipeline(this.renderer)
const scenePass = pass(this.game.scene, this.game.view.camera)
const scenePassColor = scenePass.getTextureNode('output')
this.bloomPass = bloom(scenePassColor)
this.bloomPass._nMips = this.game.quality.level === 0 ? 5 : 2
this.bloomPass.threshold.value = 1
this.bloomPass.strength.value = 0.25
this.bloomPass.smoothWidth.value = 1
```

Vibecraft, MIT, Copyright (c) 2025 nearcyan, `src/entities/animations/WorkingBehaviors.ts` (the terminal
station's loop; arm angles condensed): a work loop is a function of `progress` 0..1, not of time.
```ts
const typing: WorkingBehavior = {
  name: 'typing', loop: true, duration: 2,
  update: (parts, progress) => {
    const typePhase = (progress * 12) % 1
    parts.leftArm.rotation.x = -0.7 + Math.sin(typePhase * Math.PI * 2) * 0.1
    parts.rightArm.rotation.x = -0.7 + Math.sin((typePhase + 0.5) * Math.PI * 2) * 0.1
    const scanX = Math.sin(progress * Math.PI * 4) * 0.02 // eyes read the screen
    parts.leftEye.position.x = -0.07 + scanX
    parts.rightEye.position.x = 0.07 + scanX
    if (Math.floor(progress * 4) % 4 === 3) parts.head.rotation.x = Math.sin((progress * 4 % 1) * Math.PI) * 0.1
    parts.body.rotation.x = 0.05
  },
}
```

whatsmyagentdoing, MIT, Copyright (c) 2026 cheoyu, `web/office3d.js` lines 1188-1199: a station screen glows
in the state's colour and pulses slowly while thinking, fast while working.
```js
for (const [dk, scr] of this.screens) {
  const p = occupant.get(dk)
  const col = p ? STATUS_COLOR[p.s.status] : null
  if (col) {
    const pulse = p.s.status === 'thinking' ? 0.5 + 0.35 * Math.sin(t * 3 + p.phase) : 0.8 + 0.2 * Math.sin(t * 9 + p.phase)
    scr.material.emissive.setHex(col)
    scr.material.emissiveIntensity = pulse
  } else {
    scr.material.emissive.setHex(0x000000)
  }
}
```

ai-office, MIT, Copyright (c) 2026 Gaurav Mishra, `src/scene/OfficeScene.js` lines 968-971 (reformatted): a
terminal screen as a canvas redrawn each frame, used as a texture.
```js
c.font = '6px monospace'; c.fillStyle = hex
for (let i = 0; i < 12; i++) {
  const y = (8 + i * 6 + Math.floor(t * 5)) % (h + 10)
  c.globalAlpha = 0.3 + (i % 3) * 0.15
  c.fillText('const deploy=async()=>{await ship()}'.substr(Math.floor(t * 2 + i * 5) % 30, 22), 4, y)
}
if (Math.sin(t * 4) > 0) { c.globalAlpha = 0.8; c.fillRect(4, h - 12, 5, 7) } // cursor
```

### 2.12 Bundle cost per reference

Only the recommended stack was measured (section 3). For the others, what the code says:
- 3dokploy: the same packages as the recommendation (fiber, drei, postprocessing), so about the section 3
  figure.
- folio-2025: three 0.187 on `three/webgpu` plus Rapier physics (`@dimforge/rapier3d`, WASM); not measured.
- Claw3D: fiber + drei inside a large Next app; the scene alone not measured.
- whatsmyagentdoing: its built `public/office3d.js` is 722 KB (three + glTF loader + meshopt decoder,
  before gzip), plus the Kenney `.glb` models.
- Vibecraft (three 0.170), Factory Yard (three 0.186.1), ai-office (three r170), The Delegation (three
  WebGPU): plain three.js, not measured; three alone is most of the 251 KB in section 3.
- Holographic material: one shader on drei's `shaderMaterial`; nothing beyond fiber + drei.

## 3. Recommended stack

`three` + `@react-three/fiber` + a few `@react-three/drei` helpers + `@react-three/postprocessing`, loaded
only on the factory page (`next/dynamic` with `ssr: false`), WebGL renderer.

| Package | Latest (npm, 2026-11-14) | Licence | Added gzip, measured |
|---|---|---|---|
| `three` + `@react-three/fiber` | 0.187.0 + 9.8.2 | MIT | +251 KB over a React-only baseline of 69 KB (r3f imports all of three, so three does not tree-shake) |
| `@react-three/drei` (RoundedBox, ContactShadows, Sparkles, Trail, Float, MeshTransmissionMaterial, Instances, Html, Environment, Lightformer, Outlines, QuadraticBezierLine) | 10.7.9 | MIT | +42 KB |
| drei `Text` (troika) if 3D text is wanted | same | MIT | +44 KB more; prefer `Html` labels |
| `@react-three/postprocessing` + `postprocessing` (Bloom, TiltShift2, SMAA, ToneMapping) | 3.2.2 + 6.39.6 | MIT + Zlib | +87 KB |
| `@react-spring/three` (optional) | 10.1.2 | MIT | +16 KB |
| Whole chosen set (fiber + drei subset + Bloom, TiltShift2, SMAA) | | | 447 KB total, about **378 KB over React** |

How measured: `npm i` of exactly these versions in a scratch folder, `esbuild --bundle --minify` of a tiny
entry per layer, `gzip -9`. Not measured under Next 16's own bundler; the factory page's real chunk will
differ somewhat. None of the stack's packages carries an install script (in the probe folder only `esbuild`,
the probe's own tool, has one). Transitives worth knowing: `zustand`
5.1.0, `three-stdlib`, `troika-three-text`, `camera-controls`, `meshline`, `hls.js` (pulled by drei's video
helpers; tree-shaken out when unused), `n8ao` (ambient occlusion, comes with postprocessing).

Constraints:
- `@react-three/fiber` 9.8.2 declares `react >=19 <19.4`. Rerun is on 19.3.1: fine today, and a React 19.4
  bump will wait for a fiber release.
- WebGL, not WebGPU: pmndrs postprocessing documents `WebGLRenderer` only; WebGPU + TSL (folio-2025, The
  Delegation) means writing the post chain by hand.
- No remote assets: no `Environment preset`, no CDN fonts or HDRs; lights from `<Lightformer>` or
  `RoomEnvironment`. Any models (for example Kenney's CC0 Factory Kit, 140 files, conveyors and machines) are
  committed to the repo.

Looked at and rejected:
- Spline (`@splinetool/runtime` 2.0.183): no licence field on npm, 36 MB unpacked, scenes authored in
  Spline's own editor (how well it binds to live data was not checked).
- Babylon.js (`@babylonjs/core` 9.36.0, Apache-2.0, 74 MB unpacked) and PlayCanvas (`playcanvas` 2.24.1, MIT;
  `@playcanvas/react` 0.11.7, pre-1.0): capable, but a second engine. A GitHub search for agent scenes on
  Babylon.js, PlayCanvas, Threlte or Spline found only agent "skills" for those tools and one 8-star codebase
  city (azerturk/kodyurd, PlayCanvas); every reference worth learning from is three.js.
- Threlte (`@threlte/core` 8.7.0, MIT): Svelte; Rerun is React.
- `framer-motion-3d`: deprecated.
- Not 3D, so out: HarnessMD/munder-difflin (9.5k stars, Pixi 2D), outworked/outworked (395 stars, Phaser,
  GPL-3.0), paulrobello/claude-office (Pixi), the pixel-agents family, eliautobot/my-virtual-office (2D).
- ajsahni/agents-office (812 stars): PolyForm Noncommercial; no code may be taken.
- Not read in depth, so not ranked: jefferysha0627/agent-office-3d (130 stars, MIT, plain three.js),
  BitmapAsset/pepeclaw, Ryder-Sun/Realm, thekaroe-thailand/claude-code-3d (its `app.office.js` is the one
  other place a rounded box with canvas textures was seen: three's `RoundedBoxGeometry` + `CanvasTexture`).

## 4. A 2x2 buddy as a 3D rounded box with a face

Geometry: use three's own `RoundedBoxGeometry` (`three/addons/geometries/RoundedBoxGeometry.js`), not drei's
`<RoundedBox>`. Probed locally on three 0.187.0: three's version keeps BoxGeometry's 6 material groups
(indices 0-5) and gives each face UVs from 0 to 1, so a material array can put the face on one wall only.
drei's `<RoundedBox>` is an `ExtrudeGeometry`, which uses world-space UVs on its caps (`WorldUVGenerator`):
a face texture would land scaled by the box size and offset.

Mapping:
- One grid cell = 1 world unit. A buddy stands on 2x2 cells with `BUDDY_FOOTPRINT_SHARE` 0.8, so the box is
  1.6 x 1.6. Height and radius from `BuddyArt.tsx` line 10 (`halfW: 40`, `depth: 80 * BUDDY_HEIGHT_RATIO = 15`,
  `radius: 9`, in board pixels): with the camera below, 1 world unit is 80 / (1.6 * sqrt 2) = 35.4 px across,
  and a vertical edge shows at cos 30, so `h = 15 / (0.866 * 35.4) = 0.49`. The board rounds only the plan
  corners (9 px along a 44.7 px edge = 0.32 units); three's geometry rounds every edge and caps the radius at
  half the smallest side, so `r` about 0.2. Start from `new RoundedBoxGeometry(1.6, 0.49, 1.6, 4, 0.2)` and
  judge by eye. Translate the geometry up by `h / 2` so the group's origin sits on the floor: then `scale.y`
  stretches the block upward with the base fixed, exactly like the CSS.
- Camera: the board is 2:1 dimetric, which in 3D is an orthographic camera turned 45 degrees around the
  vertical and tilted 30 degrees down (sin 30 = 0.5 = 28/56). Then the screen-left wall is the +z face, group
  index 4: that wall gets the face, the others the body colour.
- Face: render the existing `BuddyFace` SVG to a string, draw it into a canvas once per (eyes, mouth, mood),
  use that canvas as `map` and `emissiveMap` of the face material so the eyes glow under bloom. This works
  because the face is self-contained (read in full): its gradients and the `-eye-glow` blur filter are in its
  own `<defs>` (`BuddyFace.tsx` lines 97-133), its colours are literal constants, and no `var(--...)` appears
  in `BuddyFace.tsx` or `BuddyArt.tsx`. Its motion comes from stylesheet classes (`iso-buddy-eyes`,
  `iso-buddy-lids`, `iso-buddy-pupils`), which an SVG drawn as an image does not see: the result is a still
  face, which is what the 3D version wants, since blink and glance move there. Blink and
  glance as transforms, not redraws: either draw the eyes on two small planes laid 0.001 in front of the wall
  and scale them on y (Claw3D's way), or redraw the 128 px canvas only on a blink, once every 4.6 s.
- Colours: `THREE.Color` parses hex, names and comma `rgb()` / `hsl()` only. The board's values include
  `var(--iso-buddy-body)`, `color-mix(...)` from `shade()` and space-syntax `rgb(255 255 255 / 0.94)`: resolve
  them in the browser first (read the CSS variable, or paint the string into a 1x1 canvas and read it back) and
  re-resolve on theme change.
- Copies running in parallel: the same geometry, behind the main buddy, with a transparent fresnel material
  (2.10) in the identity colour, a short delay on every motion so they trail the original, and a count in a
  label. One instanced mesh for all copies of one coworker.

Sketch (not run; Rerun's own timings from `styles.css`, no third-party code): the bob, base pinned.
```tsx
const BOB = [[0, 1], [0.35, 1.2], [0.62, 0.92], [0.78, 1.02], [1, 1]] // [share of 1.2 s, scaleY]
function sample(keys: number[][], t: number) {
  const i = keys.findIndex(k => k[0] >= t)
  const [t0, v0] = keys[Math.max(0, i - 1)], [t1, v1] = keys[i]
  const u = t1 === t0 ? 0 : (t - t0) / (t1 - t0)
  return v0 + (v1 - v0) * (u * u * (3 - 2 * u)) // smoothstep in place of the CSS cubic-bezier
}
function Buddy({ mood, delay, still }: { mood: BuddyMood; delay: number; still: boolean }) {
  const body = useRef<THREE.Group>(null!)
  useFrame(({ clock }) => {
    if (still || mood !== 'working') { body.current.scale.y = 1; return }
    const t = ((clock.elapsedTime + delay) % 1.2) / 1.2
    body.current.scale.y = sample(BOB, t)
  })
  return <group ref={body}>{/* mesh with RoundedBoxGeometry translated up by h / 2 */}</group>
}
```

(`working` maps to bob and `error` to shudder in `TileBuddy.tsx` line 20 and `AgentBuddy.tsx` line 29.)

## 5. Techniques, and where each comes from

1. **Orthographic 2:1 camera with fit-to-content zoom.** `<Canvas orthographic>`, camera yawed 45 and pitched
   30 degrees; zoom computed from the scene's bounds, negative near plane so zooming out never clips the floor.
   From 3dokploy `src/scene/Scene.tsx` (fit function near line 175, `near: -1000`).
2. **Squash and stretch with a pinned base.** Geometry raised by half its height, then `scale.y` from Rerun's
   own keyframes (section 4). Appear/vanish by `scale.setScalar` over 0.35 s: 3dokploy `Agents.tsx` line 145.
3. **Glow only where meant.** Emissive colour above 1 plus `toneMapped={false}`, then `<Bloom mipmapBlur
   luminanceThreshold={0.9..1}>` so only those parts bloom; keep strength low (folio-2025 uses 0.25).
   From 3dokploy `Scene.tsx` line 103, pmndrs `confetti`, folio-2025 `Rendering.js` lines 81-85.
4. **Jobs as objects on routes.** A path follower that steps by `speed * dt` along polyline points, damped
   heading, a small bounce while moving, a dock state, and a return trip; simulation in refs, React state only
   on phase changes. 3dokploy `Agents.tsx` (`Walker`, `dampAngle`); Factory Yard keeps the simulation in its
   own folder (`yard/sim`).
5. **Show the selected job's road.** Draw the remaining route dashed on the floor and mark the next station.
   Factory Yard (screenshot `docs/factory-yard.png`).
6. **Working stations.** A light column with travelling bands and a spinning floor ring over a station that is
   busy (3dokploy beam shader); per-station work loops for the worker standing there (Vibecraft
   `WorkingBehaviors.ts`); live screens as `CanvasTexture` (ai-office `OfficeScene.js` 960-995).
7. **One-off event pulses.** A ring that grows and fades once when a job ends, green or red; only for events
   that arrive after mount, so a page load is quiet. 3dokploy `Effects.tsx` (`Pulses`, `PULSE_S = 1.8`).
   Rerun's merge celebration = this ring plus a burst of `<Sparkles>` or the `confetti` ribbons.
8. **Cables, comets and belts.** A curve that follows two moving ends each frame (`backdrop-and-cables`), with
   a scrolling dash or a small emissive sphere riding it as the comet (`confetti` dash offset; drei `<Trail>`
   for a fading tail behind the sphere). Belts: none of the references read has a conveyor in code. The same
   trick applies: a repeating stripe texture on the belt mesh with `map.offset.x += speed * dt`, belt models
   from Kenney's CC0 Factory Kit if wanted. Own proposal, untested.
9. **Faces that blink by state.** Per-agent seed for the blink phase, eye openness and mouth shape by state.
   Claw3D `agents.tsx` lines 372-430 (port it to `delta` time).
10. **See-through copies.** Fresnel/scanline material for copies (holographic material, 2.10), drei
    `<MeshTransmissionMaterial>` if glass is wanted (costlier: an extra render per frame), one `InstancedMesh`
    per coworker's copies.
11. **Held line** (own proposal; no reference shows one). Desaturate and slow the world rather than add a banner inside it: conveyors stop, beams
    fade to a still amber, workers' bob stops and eyes droop (the `asleep` mood), a striped barrier mesh drops
    across the merge gate. The 2D hold band stays in the HTML above the canvas.
12. **Miniature look.** `<TiltShift2>` blurs top and bottom so the factory reads as a model on a table
    (pmndrs `tilt-shift`, which pairs it with a fov-30 perspective camera; untested over an orthographic one).
    Optional; check that labels stay legible.
13. **Light and shadow with no downloads.** `<Environment resolution={128} frames={1}>` filled with
    `<Lightformer>` panels (3dokploy `Scene.tsx` lines 61-65) or `PMREMGenerator.fromScene(new RoomEnvironment())`
    (claude-code-3d `app.office.js` line 57); drei `<ContactShadows>` under the buddies, or one directional
    light whose orthographic shadow camera is sized to the floor (3dokploy `Scene.tsx` line 56), map 1024-2048.
14. **Text over 3D as HTML.** drei `<Html>` labels for names, job numbers and timers, as 3dokploy's `Label`
    and whatsmyagentdoing's canvas overlay do: crisp text, theme CSS, no 44 KB font engine.
15. **Calm by default.** Clamp `dt` to 0.1, a `reducedMotion` flag that every `useFrame` checks (3dokploy),
    `frameloop="demand"` when nothing moves, `dpr={[1, 2]}`, `<PerformanceMonitor>` to drop bloom on weak GPUs.

## 6. Verdict

- **Build the factory view in react-three-fiber, starting from 3dokploy's structure, dressed in Rerun's
  buddies.** It is the only reference with Rerun's exact stack and versions, jobs that travel to stations and
  back, busy-station beams, end-of-job pulses and a reduced-motion switch, under MIT. Take the look's
  restraint from folio-2025, the parallel-copies layout from Vibecraft, the route display from Factory Yard
  and the face logic from Claw3D.
- **Case for staying in DOM/CSS:** the current board already bobs, blinks, glances and runs comets on cables at
  zero bundle cost, is accessible, and themes through CSS variables. The 3D view adds about 378 KB gzip (lazy,
  page-only), a second way to draw a buddy that must stay in step with the first, and GPU cost on weak
  laptops. It is worth it only as a separate page, never as a replacement for the board.
- **Confidence: medium.** The references, licences, versions and sizes are checked at the source and by a
  local probe. Not proven: that a rounded box with an SVG face texture keeps the buddy's charm in 3D, and what
  the page costs on a weak GPU. Both are settled by one spike.
- **Next step:** a spike on a branch: `/factory` page, `next/dynamic` with `ssr: false`; one orthographic
  canvas; three stations in a row (build, review, checks) and a merge gate; one buddy from the board's own
  `BuddyFace` on `RoundedBoxGeometry` with the bob; two see-through copies; one job box travelling the line
  with `Walker`; bloom only on emissive parts. Measure the page chunk under Next 16 and the frame time on an
  integrated GPU, then show it to the owner beside the DOM board.
