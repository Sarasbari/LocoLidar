# Neo-Brutalism UI Revamp

## Goal
Redesign the frontend from a dark "AI-slop" gradient theme to a high-contrast Neo-Brutalism aesthetic with stark colors, thick black borders, hard shadows, and bold typography.

## Tasks

- [ ] Task 1: Update CSS variables and base styles → Verify: Body has an off-white/beige background (e.g., `#f4f0e6`), no radial gradients, and text is stark black or dark gray. Font changed to a grotesque or monospace family.
- [ ] Task 2: Restyle layout panels and containers → Verify: Panels have solid background colors (white or bright accents), thick black borders (`3px solid #000`), and hard drop shadows (`4px 4px 0px #000`) instead of gradients/blur.
- [ ] Task 3: Restyle interactive elements (buttons, inputs, selects) → Verify: Buttons have thick borders, sharp corners, and a brutalist hover state (e.g., translating down/right and removing the shadow to simulate a physical press).
- [ ] Task 4: Restyle typography, tags, and metrics → Verify: Headings, tags, and risk metrics are uppercase, bold, and use stark contrasting background colors without soft rounded pills.
- [ ] Task 5: Update `app.js` canvas rendering for light mode → Verify: Canvas background changed from `#070b12` to a light color (e.g., `#ffffff` or the neo-brutalism bg). Grid lines, points, and hazard rings updated to contrast well against the light background.
- [ ] Task 6: Test UI locally → Verify: `npx serve web -l 5500` displays the new UI correctly, all text is readable, components don't overlap awkwardly, and the canvas animation looks cohesive with the new theme.

## Done When
- [ ] All gradients, soft shadows, and rounded dark-theme elements are removed from `web/styles.css`.
- [ ] UI features thick black borders and hard shadows.
- [ ] Canvas rendering in `web/app.js` is updated to match the light, high-contrast theme.
- [ ] The app looks distinctly Neo-Brutalist and runs without styling errors.

## Notes
- Neo-Brutalism relies on high contrast. Use colors like `#ff90e8` (pink), `#ffc900` (yellow), `#000000` (black), and `#ffffff` (white).
- Avoid `border-radius` greater than `4px` unless intentionally mixing shapes.
- Keep the `metrics.json` fetching and core logic in `app.js` perfectly intact; only modify the `draw()` and `render()` styling logic.

