# Metamorphic Labs Brand System (For all SaaS & main company)

This document defines the canonical brand tokens, usage rules, and UI patterns for all Metamorphic Labs properties. All new development must use these tokens exclusively.

## Brand Essence

- Personality: precise, dependable, and quietly confident
- Aesthetic: dark, minimal, high‑contrast with cyan/teal highlights
- Motion: subtle, purposeful; never flashy

## Color Tokens (Hex + HSL)

Primary palette
- `--brand-primary` (#11C8D6, hsl(186, 85%, 46%))
- `--brand-primary-600` (#0FB2BF, hsl(185, 84%, 40%))
- `--brand-primary-700` (#0C96A1, hsl(185, 84%, 34%))

Surfaces & borders
- `--surface-0` background: #0B1116 (hsl(208, 32%, 6%))
- `--surface-1` panels: #111821 (hsl(210, 30%, 9%))
- `--surface-2` raised: #151E28 (hsl(209, 29%, 12%))
- `--line-1` borders: #1E2A36 (hsl(208, 28%, 17%))
- `--line-2` dividers: #223445 (hsl(208, 31%, 20%))

Typography
- `--fg-strong` #E6EEF5 (hsl(205, 40%, 93%))
- `--fg` #C7D4E2 (hsl(210, 32%, 82%))
- `--fg-muted` #95A3B5 (hsl(213, 18%, 65%))

States
- `--focus` #11C8D6
- `--success` #22C55E
- `--warning` #F59E0B
- `--danger` #EF4444

Opacity helpers
- `--glow-primary` rgba(17, 200, 214, 0.15)
- `--overlay` rgba(0, 0, 0, 0.35)

## Typography

- Primary: Inter, system‑ui, sans‑serif
- Weights: 400 (body), 500 (UI), 600/700 (headings)
- Tracking: normal; avoid negative letter‑spacing
- Sizes (clamp):
  - Display: clamp(42px, 8vw, 76px) / clamp(50px, 8vw, 84px)
  - H2: 20/28
  - H3: 16/22
  - Body: 15/24
  - Small: 12/20

## Spacing & Radii

- Grid: 4px base units
- Radii: 12px buttons, 14px cards, 10px inputs
- Shadows: very subtle; prefer border+glow rather than heavy shadow

## Components

Navigation
- Top bar and side bar use `--surface-1` with `--line-1` borders
- Active tab: `--brand-primary` underline (2px); inactive tabs `--fg-muted`

Buttons
- Primary: bg `--brand-primary`, hover `--brand-primary-600`, text `--surface-0`
- Secondary: bg `--surface-2`, border `--line-1`, text `--fg`
- Focus ring: 2px `--brand-primary` at 40% opacity

Cards/Panels
- Bg `--surface-1`, border `--line-1`, radius 14px, optional glow `--glow-primary`

Inputs
- Bg `--surface-2`, border `--line-1`, text `--fg`, placeholder `--fg-muted`

Badges/Pills
- Bg `--surface-2`, border transparent, text `--brand-primary`

## Accessibility

- Minimum contrast 4.5:1 for text on all surfaces
- Hover should not be the only indicator of interactivity
- Respect `prefers-reduced-motion` and `prefers-contrast`

## Implementation

CSS custom properties (authoritative source) are defined in `shared/styles/globals.css`. Tailwind 4 consumes them via utility classes or inline CSS.

Use these semantic classes/vars:
- Backgrounds: `bg-[color:var(--surface-0)]`, `bg-[color:var(--surface-1)]`
- Text: `text-[color:var(--fg)]`, `text-[color:var(--fg-muted)]`
- Borders: `border-[color:var(--line-1)]`
- Accent: `text-[color:var(--brand-primary)]`, `border-[color:var(--brand-primary)]`

Do not hard‑code hex values in components. Always reference tokens.

## Logo & Iconography

- Wordmark: VERIFORGE in Inter SemiBold with +2% letter spacing
- Mark: circular compass slash on `--surface-1` with `--brand-primary` stroke
- Clear space: 1× cap height around the mark and wordmark
- Minimum size: 24px height in nav, 16px for badges

## Motion

- Durations: 150–200ms; easing: `cubic-bezier(0.2, 0.8, 0.2, 1)`
- Use `--glow-primary` for subtle emphasis on active elements

## Do / Don’t

Do
- Keep surfaces subtle and consistent
- Use primary cyan sparingly to call attention

Don’t
- Introduce other accent colors
- Use bright shadows or gradients not specified here

---

All new components must consume these tokens via CSS variables or shared utilities. Submit PRs that introduce new colors to brand review.
