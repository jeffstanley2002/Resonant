---
version: "1.0"
name: "Resonant"
description: "A dark, evidence-led Singapore career workspace that turns resume signals into focused action."
colors:
  canvas: "#090A0F"
  surface: "#11131A"
  surface-raised: "#171A23"
  line: "#292E3D"
  ink: "#F7F8FC"
  muted: "#A8AFC0"
  primary: "#4D7CFE"
  signal: "#FF6B5E"
  coaching: "#F2B94B"
  danger: "#FF5F68"
typography:
  display:
    fontFamily: '"Iowan Old Style", "Palatino Linotype", Georgia, serif'
  sans:
    fontFamily: '"Avenir Next", Avenir, "Segoe UI", Helvetica, Arial, sans-serif'
  mono:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
rounded:
  DEFAULT: "8px"
  control: "6px"
  tag: "5px"
spacing:
  app-header: "68px"
  app-max: "1640px"
  landing-max: "1480px"
components:
  button: {}
  card: {}
  dialog: {}
  tabs: {}
  upload: {}
---

# Resonant Design System

## Overview

### Creative North Star

Resonant borrows from a focused night-time career studio: dark work surfaces, precise cobalt wayfinding, coral priority signals, and amber coaching cues. It should feel ambitious and composed, not like a developer console or a generic template dashboard.

### Product context and register

- **Audience and primary job:** Students, early-career candidates, and career switchers turning a resume into a realistic application plan.
- **Target market and evidence:** Singapore is the default market by explicit product request; live search routes through MyCareersFuture-compatible sources.
- **Locale and language policy:** English UI, Singapore location defaults, plain action-first copy.
- **Usage scene:** Desktop-first analysis with complete mobile reflow for repeated job-search sessions.
- **Register:** Public landing experience for signed-out visitors; focused product workspace after authentication.
- **Memorable signature:** The career signal map connects resume evidence, ranked matches, repeated gaps, and coaching actions.
- **Restraint:** Forms, tabs, job lists, warnings, and destructive actions remain familiar and quiet.
- **Anti-references:** No pale generic SaaS card wall, anonymous metrics, neon cyberpunk effects, purple gradients, or dominant green/teal palette.
- **Token ownership/runtime mapping:** This file owns visual intent; implemented tokens live in `apps/web/app/globals.css`. The premium static audit is the drift gate.

## Colors

The interface is dark by default. Canvas and surface tokens create hierarchy through tone and borders, not gradients. Cobalt is the primary interaction color, coral marks ranking and skill-gap priority, amber identifies coaching and feedback, and danger is reserved for destructive actions. Focus uses a high-contrast amber ring. Forced-colors mode returns border decisions to the system.

## Typography

Iowan Old Style is used sparingly for high-level landing and workspace statements. Avenir Next and its system fallbacks own controls, body copy, and dense job content. Monospace is reserved for ranks, counts, and technical run data. Letter spacing is always zero; headings gain character through family, scale, and line-height rather than compression.

## Layout

The public hero is full-bleed inside a small page frame and always leaves the next content band discoverable. The authenticated workspace uses a 355px setup rail beside a flexible results region, then becomes one document-scrolling column below 780px. Match lists use explicit progressive disclosure in groups of eight while preserving the full result count.

## Elevation & Depth

Most hierarchy comes from tonal surfaces and one-pixel borders. Strong shadow and background blur are limited to the hero frame, sticky header, and modal dialogs. Repeated job cards do not float independently.

## Shapes

Panels and dialogs use an 8px radius, controls use 6px, and compact tags use 5px. Circular geometry is reserved for small counts where the value itself is the object. Match score is a labeled typographic block, not an unexplained circle.

## Components

### Foundational visual states

Interactive controls define hover, focus-visible, active, disabled, selected, busy, success, and error states. Busy controls preserve their dimensions and use a rotating Lucide loader. Empty states reserve stable space and explain the next action.

### Buttons and actions

Cobalt solid buttons are primary actions. Outlined surface buttons are secondary actions. Coral is a landing conversion signal, and danger red is reserved for the final delete confirmation. Icons accompany commands when they improve scanning.

### Navigation and data display

Landing navigation visibly separates Log in and Sign up. Authenticated navigation keeps identity and Sign out in the top bar. Workspace tabs use proper tab semantics and arrow-key navigation. Counts always include their object or accessible label.

### Forms and overlays

Forms use app-owned validation with associated errors and `noValidate`. Sign-up requires password confirmation and shows the password requirement before submission. Password fields support show/hide, paste, and password managers. Destructive confirmation uses an app-owned native dialog with safe initial focus.

### Iconography

Lucide React is the only icon family. Icons use 14-23px sizes depending on context, remain decorative when adjacent text supplies the label, and never replace an unfamiliar command label.

### Motion

Framer Motion handles one orchestrated landing reveal, tab-panel transitions, and result arrival. Most transitions run for 160-220ms; the landing reveal may run up to 650ms. All motion honors reduced-motion preferences and never blocks interaction.

### Content and data visualization

Copy speaks from the job seeker's perspective. Match percentages are labeled “Match score” and explicitly described as directional. Skill-gap frequency reads “requested by X of Y matched roles.” Feedback uses five named usefulness levels instead of context-free numbers.

## Do's and Don'ts

- **Do:** Connect every score and count to its meaning in visible or accessible text.
- **Do:** Preserve the evidence → gaps → coaching relationship across tabs.
- **Don't:** Lead with test counts, provider names, model costs, or implementation proof.
- **Don't:** use ornamental gradients, oversized dashboard metrics, nested cards, or unlabeled icon controls.
