---
name: Spotify Review Discovery Engine
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#393939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#bccbb9'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#869585'
  outline-variant: '#3d4a3d'
  surface-tint: '#53e076'
  primary: '#53e076'
  on-primary: '#003914'
  primary-container: '#1db954'
  on-primary-container: '#004118'
  inverse-primary: '#006e2d'
  secondary: '#c8c6c5'
  on-secondary: '#303030'
  secondary-container: '#474746'
  on-secondary-container: '#b7b5b4'
  tertiary: '#c8c6c6'
  on-tertiary: '#303030'
  tertiary-container: '#a2a1a1'
  on-tertiary-container: '#383838'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#72fe8f'
  primary-fixed-dim: '#53e076'
  on-primary-fixed: '#002108'
  on-primary-fixed-variant: '#005320'
  secondary-fixed: '#e5e2e1'
  secondary-fixed-dim: '#c8c6c5'
  on-secondary-fixed: '#1b1b1c'
  on-secondary-fixed-variant: '#474746'
  tertiary-fixed: '#e4e2e2'
  tertiary-fixed-dim: '#c8c6c6'
  on-tertiary-fixed: '#1b1c1c'
  on-tertiary-fixed-variant: '#474747'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-kpi:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
  section-header:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  container-max-width: 1440px
  margin-x: 2rem
  gutter: 1.5rem
  panel-padding: 1.5rem
  stack-gap: 1rem
---

## Brand & Style
The design system establishes a high-performance, B2B intelligence environment. It is a tool for data-driven decision-making, moving away from consumer-grade entertainment aesthetics toward a professional "Discovery Intelligence" platform. 

The visual style is **Corporate / Modern** with a focus on data density and information hierarchy. It utilizes a refined Dark Mode interface that prioritizes legibility and focus. The aesthetic is characterized by a "Flat Plus" approach—flat surfaces with subtle depth cues, purposeful use of the signature green accent to guide action, and a structured, systematic grid that evokes trust and precision for product managers and researchers.

## Colors
The palette is rooted in a deep charcoal and black foundation to minimize eye strain during long research sessions. 

- **Foundation:** The primary background uses a pure dark base, while panels and cards use a slightly elevated grey to create visual containers.
- **Accents:** Spotify Green is used surgically—only for primary actions, active navigation states, and "positive" data trends.
- **Data Visualization:** The chart palette is distinct from the UI furniture, ensuring that multi-series data remains readable and accessible against the dark background.
- **Typography Colors:** White (#FFFFFF) is reserved for high-priority headings and data points, while Secondary Grey (#B3B3B3) handles all descriptive and meta-content to maintain a clean hierarchy.

## Typography
The system uses **Inter** for its exceptional legibility in data-heavy contexts and its neutral, professional tone. 

- **KPI Hierarchy:** Large numerical values (KPIs) utilize the `display-kpi` style to immediately draw the eye to core metrics.
- **Scale:** Font sizes are kept tight (14px/16px) for body text to allow for high information density without sacrificing readability.
- **Contrast:** Headings are always White (#FFFFFF) to provide a clear entry point for each section, while body text uses the secondary grey to reduce visual noise.
- **Labels:** Small caps are used for chart axes and table headers to provide a distinct stylistic break from standard body text.

## Layout & Spacing
The layout follows a **Fluid Grid** model with a maximum width of 1440px for desktop optimization.

- **Sidebar:** A fixed 260px left-hand navigation allows for quick switching between research modules.
- **Grid:** A 12-column system is used for dashboard widgets. KPIs typically span 3 columns, while complex charts or "Theme Explorer" tables span 6 to 9 columns.
- **Rhythm:** A 4px/8px base scaling system is applied. Cards use 24px (1.5rem) internal padding to ensure data density feels intentional rather than cramped.
- **Mobile/Tablet:** On smaller screens, the 12-column grid collapses to a single column, and horizontal margins reduce to 16px.

## Elevation & Depth
Depth is conveyed through **Tonal Layers** rather than heavy shadows.

- **Level 0 (Base):** Background (#121212).
- **Level 1 (Panels):** Surface cards (#1E1E1E) with a subtle 1px border (#2E2E2E) to define edges.
- **Level 2 (Modals/Popovers):** Higher elevation (#2A2A2A) with a soft, 15% opacity black shadow (0px 8px 24px) to create separation from the dashboard surface.
- **Interaction:** Hover states on interactive cards should use a subtle background shift to #252525 rather than an upward float.

## Shapes
The shape language is **Rounded**, balancing professional structure with modern software aesthetics.

- **Standard Elements:** Cards, input fields, and buttons use a 0.5rem (8px) corner radius.
- **Large Containers:** Hero sections or large data panels can scale up to 1rem (16px) if they contain nested elements.
- **Data Points:** Markers on line charts and small status indicators (chips) use a full pill shape for clear distinction from structural UI boxes.

## Components
- **Buttons:** Primary buttons are Solid Green (#1DB954) with Black text. Secondary buttons are Ghost style with a White border.
- **Input Fields:** Dark grey backgrounds (#252525) with a 1px border. Focus state triggers a Green border-glow.
- **Chips / Tags:** Low-contrast backgrounds (Secondary Grey at 10% opacity) with Secondary Grey text for metadata; use colored backgrounds only for sentiment (Green = Positive, Red = Negative).
- **Navigation:** Vertical sidebar using 20px icons and 14px Medium weight text. Active state uses a left-aligned 4px Green vertical bar.
- **Cards:** No outer shadows on base dashboard cards; use a 1px border (#333333). Internal headers should be separated by a subtle divider line.
- **Research Assistant:** A specialized floating panel or docked side-drawer with a slight gradient border to signify AI-powered functionality.
- **Data Tables:** Zebra-striping is avoided; use subtle hover rows and 1px horizontal dividers only.