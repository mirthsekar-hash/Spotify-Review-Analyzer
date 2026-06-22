# Google Stitch UI Generation Prompt

**Project:** Spotify Review Discovery Engine  
**Stitch project:** [Spotify Review Discovery Engine (Stitch)](https://stitch.withgoogle.com/projects/17597949978679283566)  
**Purpose:** Generate high-fidelity UI mockup images for a Product Research Intelligence Platform (Streamlit web app).  
**How to use:** Paste the **Master Design System** block first in Stitch to set style, then paste individual **Screen prompts** one at a time (or ask Stitch for a multi-screen flow using the full list at the bottom).

---

## Master Design System (paste this first)

```
Design a professional B2B analytics dashboard web application called "Spotify Review Discovery Engine" — an AI-powered Product Research Intelligence Platform for Spotify music discovery insights.

VISUAL STYLE:
- Dark mode analytics product (not a consumer music player UI)
- Desktop web app, 1440px wide, wide layout
- Modern, clean, data-dense but readable — think Mixpanel, Amplitude, or Notion Analytics meets Spotify brand accents
- Flat UI with subtle cards, rounded corners (8–12px), soft shadows
- Professional product-management / user-research audience

COLOR PALETTE (use exactly):
- Background: #121212
- Card / panel background: #1E1E1E
- Primary accent / CTAs / active nav: #1DB954 (Spotify green)
- Secondary text: #B3B3B3
- Primary text: #FFFFFF
- Warning: #F59E0B amber
- Error: #EF4444 red
- Info: #3B82F6 blue
- Chart colors: green #1DB954, red #E91429, gray #535353, blue #509BF5, purple #A855F7

TYPOGRAPHY:
- Sans-serif: Inter or similar
- Page titles: bold 28–32px white
- Section headers: semibold 18–20px white
- Body: 14–16px #B3B3B3
- KPI numbers: bold 32–40px white or green

LAYOUT PATTERN (all screens):
- Left sidebar (240px): dark #1E1E1E, app logo "🎧 Spotify Review Engine", subtitle "AI Product Research Intelligence Platform"
- Sidebar sections: Pipeline Actions (primary green buttons), Database status (green "Supabase connected"), Configuration (LLM + Embeddings labels)
- Main content area: #121212 with generous padding
- Use KPI metric cards in a 4-column grid where relevant
- Charts: bar charts, donut/gauge charts, Sankey diagrams — Plotly-style, dark theme
- Evidence citations: expandable review cards with source badges (Play Store green, App Store blue, Reddit orange)

ICONS (emoji or line icons OK):
📊 Executive Summary | 📁 Source Analysis | 🔍 Discovery Challenges | 🏷️ Theme Explorer | 👥 Segment Explorer | 🎯 Root Cause Analysis | 💡 Unmet Needs | 🗺️ Discovery Journey | ✅ Interview Validation | 🤖 Research Assistant

Do NOT design a Spotify music player. This is a research analyst dashboard that ingests Play Store, App Store, and Reddit reviews about Spotify.
```

---

## Screen 1 — Executive Summary

```
[Use Master Design System above]

Screen: Executive Summary dashboard

HEADER:
- Title: "Executive Summary"
- Subtitle: "Product research intelligence across ingested Spotify feedback"
- Health indicator strip: green dot "DB connected" | last ingestion timestamp | last analysis timestamp

AI EXECUTIVE SUMMARY PANEL (prominent card at top):
- Section title: "AI Executive Summary"
- 2–3 sentence AI-generated summary paragraph
- Subsections: "Key Findings" (3 bullet points), "Top Opportunity" (1 highlighted callout in green border)
- Caption: "Grounded in 8 themes, 5 segments, 6 root causes, 3 unmet needs"

KPI ROW (4 cards):
1. "Reviews Analyzed" — large number 49, delta "12 pending"
2. "Top Discovery Challenge" — "Repetitive recommendations"
3. "Most Affected Segment" — "Music Explorer (62% neg)"
4. "Recommendation Trust" — gauge-style score 58/100

LOWER SECTION (2 columns):
- Left: "Sentiment Breakdown" stacked bar or donut chart (positive 22%, negative 45%, neutral 20%, mixed 13%)
- Right: "Trust Score" circular gauge chart in Spotify green

FOOTER DETAIL:
- "Top Challenge Detail" — "Repetitive recommendations appears in 18 analyzed reviews"

Show realistic placeholder data. Polished, demo-ready PM dashboard.
```

---

## Screen 2 — Source Analysis

```
[Use Master Design System]

Screen: Source Analysis — compare feedback by Play Store, App Store, Reddit

HEADER: "Source Analysis" | subtitle "Review volume and sentiment by ingestion source"

THREE SOURCE CARDS in a row:
- Play Store (green badge): 120 reviews, 45 analyzed, avg rating 3.2, rec-complaint 38%
- App Store (blue badge): 80 reviews, 30 analyzed, avg rating 2.8, rec-complaint 52%
- Reddit (orange badge): 50 reviews, 25 analyzed, sentiment score -0.3

Below: grouped bar chart comparing sentiment distribution per source

Table: "Top complaints by source" with columns Source | Primary problem | Count

Dark analytics aesthetic, clear source color coding throughout.
```

---

## Screen 3 — Discovery Challenges

```
[Use Master Design System]

Screen: Discovery Challenges — ranked table of user discovery pain points

HEADER: "Discovery Challenges" | subtitle "Most frequent discovery_challenge values from analyzed reviews"

RANKED DATA TABLE:
Columns: Rank | Challenge | Frequency | Negative % | Affected segments | Avg sentiment
Rows example:
1. Repetitive recommendations | 24 | 71% | Music Explorer, Casual Listener | -0.6
2. Stale Discover Weekly | 18 | 65% | Music Explorer | -0.5
3. Shuffle plays same songs | 12 | 80% | Playlist-Dependent Listener | -0.7

Impact badges: red "High impact" for top rows, amber "Medium" for mid

Optional: horizontal bar chart of top 10 challenges by frequency

Clean data-table-first layout, sortable column headers suggested visually.
```

---

## Screen 4 — Theme Explorer

```
[Use Master Design System]

Screen: Theme Explorer — drill into collective AI-extracted themes

HEADER: "Theme Explorer" | subtitle "Discovery themes from collective analysis"

LEFT (40%): scrollable theme list cards
- Each card: theme name, frequency, impact score badge (e.g. 82/100 in green), affected segment pills
- Selected card highlighted with green left border: "Stale Discover Weekly"

RIGHT (60%): theme detail panel
- Theme title + impact badge
- Segment distribution pie chart
- "Supporting evidence" — 3 expandable review excerpts with Play Store / Reddit badges and star ratings
- "Related root causes" and "Related unmet needs" link lists

Segment pills examples: Music Explorer, Casual Listener, Playlist-Dependent Listener

Explorer / master-detail layout pattern.
```

---

## Screen 5 — Segment Explorer

```
[Use Master Design System]

Screen: Segment Explorer — user segment profiles

HEADER: "Segment Explorer" | subtitle "Listening goals, behaviors, and frustrations by segment"

5 SEGMENT CARDS in responsive grid:
Each card titled with segment name and size count:
- Casual Listener (size 15)
- Playlist-Dependent Listener (size 12)
- Music Explorer (size 20) — highlighted
- Genre Loyalist (size 8)
- Power User (size 6)

Inside each card:
- Listening goals (bullet list)
- Discovery behavior (bullet list)
- Top frustrations (bullet list, red accent)
- Recommendation trust score: progress bar

Selected segment expands below with sample negative review quotes as evidence list.

Persona-card aesthetic, PM-friendly segment taxonomy.
```

---

## Screen 6 — Root Cause Analysis

```
[Use Master Design System]

Screen: Root Cause Analysis — systemic causes of discovery failures

HEADER: "Root Cause Analysis" | subtitle "Underlying systemic causes of discovery failures"

RANKED TABLE:
Columns: Rank | Root cause | Frequency | Evidence reviews | Affected segments
Example rows:
1. Algorithm overfits past listening history | 14 | 12 | Music Explorer, Genre Loyalist
2. Limited shuffle pool rotation | 9 | 8 | Playlist-Dependent Listener
3. Discover Weekly refresh cadence too slow | 7 | 6 | Music Explorer

Below table: dropdown "Evidence panel" selector
Selected root cause detail with segment badges and expandable supporting review list (evidence timeline style)

Analytical, cause-and-effect research tone.
```

---

## Screen 7 — Unmet Needs

```
[Use Master Design System]

Screen: Unmet Needs — product opportunity discovery

HEADER: "Unmet Needs" | subtitle "Emerging needs and AI solution opportunities"

OPPORTUNITY MATRIX or ranked cards sorted by opportunity score:
Each need card shows:
- Need title: "Fresh weekly discovery mixes with explicit novelty control"
- Frequency: 11
- Opportunity score: 0.85 (green progress bar)
- Suggested AI solutions: 2–3 bullet chips
- Supporting review count

Layout: 2-column card grid, highest opportunity at top-left

Highlight top opportunity with green "Top bet" badge.

Innovation / opportunity framing, startup-meets-PM-research style.
```

---

## Screen 8 — Discovery Journey

```
[Use Master Design System]

Screen: Discovery Journey — user goal to challenge flow

HEADER: "Discovery Journey" | subtitle "How user goals connect to discovery challenges"

HERO VISUALIZATION: Sankey diagram (dark theme, green flows)
- Left nodes: user goals ("Discover new artists", "Find workout music", "Break out of repeat playlists")
- Right nodes: discovery challenges ("Stale recommendations", "Poor shuffle", "Filter bubble")
- Flow width = frequency

Below Sankey: summary stats row
- "Top goal–challenge gap" callout card
- Mini table of top 5 gaps with counts

Data storytelling layout, flow diagram as centerpiece. Plotly Sankey style on dark background.
```

---

## Screen 9 — Interview Validation

```
[Use Master Design System]

Screen: Part 2 — User Research Validation

HEADER: "Part 2 — User Research Validation"
Subtitle: "Compare qualitative interview findings with review evidence from collective themes"

TOP: "Add interview insight" form card
Fields: Insight (textarea), Linked theme (dropdown), Interview validation % (slider 0–100), Confidence score (0–1), Notes
Green primary button: "Add insight"

BOTTOM: "Interview vs. review evidence" comparison table
Columns: Insight | Linked theme | Review evidence | Interview validation % | Confidence score | Notes
Example row:
"Users say Discover Weekly feels the same every week" | Stale Discover Weekly | 8 reviews | 85% | 0.82 | "5 participants, remote"

Empty-state variant (optional second image): friendly info box with numbered instructions how to use the page.

Qualitative + quantitative validation UX, clean form above data table.
```

---

## Screen 10 — Research Assistant (RAG Chat)

```
[Use Master Design System]

Screen: AI Research Assistant — conversational RAG with citations

HEADER: "AI Research Assistant"
Subtitle: "Ask questions about Spotify user reviews in this dataset — answers grounded in Play Store, App Store, and Reddit feedback"

TWO-COLUMN LAYOUT (65% / 35%):

LEFT — Chat column:
- "Suggested questions" — 6 clickable pill/chip buttons in 2 columns
  Examples: "Why do users struggle to discover new music?", "What causes repetitive listening?"
- Chat history:
  - User bubble (right-aligned, dark gray): question text
  - Assistant bubble (left-aligned, card): 
    - Summary paragraph
    - Sections: Key themes, Root causes, Affected segments (pills), Product opportunities
    - Confidence meter: 78% green progress bar
- Bottom: chat input field "Ask about Spotify reviews, discovery, or user feedback..."

RIGHT — Citations sidebar:
- Title: "Citations"
- 3 expandable citation cards:
  - "🟢 Play Store · ★ 2 · Music Explorer" — excerpt + full review text
  - "🟠 Reddit · ★ 1 · Music Explorer"
  - "🔵 App Store · ★ 3 · Casual Listener"
- "Clear chat" secondary button at bottom

ChatGPT-meets-analytics aesthetic, evidence-first AI assistant, Spotify-green send/active states.
```

---

## Sidebar (shared across all screens)

```
[Use Master Design System]

Component: Left sidebar navigation panel (standalone or included in every screen)

CONTENT:
- App branding: 🎧 Spotify Review Engine
- Subtitle: AI Product Research Intelligence Platform

NAV LIST (vertical, icon + label):
📊 Executive Summary (active — green highlight)
📁 Source Analysis
🔍 Discovery Challenges
🏷️ Theme Explorer
👥 Segment Explorer
🎯 Root Cause Analysis
💡 Unmet Needs
🗺️ Discovery Journey
✅ Interview Validation
🤖 Research Assistant

PIPELINE ACTIONS section:
- Primary green button: "Fetch Latest Reviews"
- Secondary buttons: Fetch Play Store, Fetch App Store, Fetch Reddit, Import CSV
- "Run Analysis" button
- "Re-run Collective Analysis" button

STATUS section:
- "Supabase connected" green success badge
- Total in DB: 250 | Play: 120 | App: 80 | Reddit: 50
- LLM: groq / llama-3.3-70b-versatile
- Embeddings: gemini / gemini-embedding-001

Dark sidebar, green active nav indicator, compact operational controls.
```

---

## Bonus — Full App Overview (single Stitch request)

```
[Use Master Design System]

Generate a 3×4 grid of small screen thumbnails showing the complete "Spotify Review Discovery Engine" web application:

Row 1: Executive Summary (KPIs + AI summary), Source Analysis (3 source cards), Discovery Challenges (ranked table), Theme Explorer (master-detail)

Row 2: Segment Explorer (persona cards), Root Cause Analysis (ranked causes), Unmet Needs (opportunity cards), Discovery Journey (Sankey diagram)

Row 3: Interview Validation (form + comparison table), Research Assistant (chat + citations sidebar), Sidebar navigation close-up, Mobile-not-required note card

Unified dark theme #121212, accent #1DB954, professional PM analytics product, desktop 1440px, consistent component library across all thumbnails. Label each thumbnail with screen name below.
```

---

## Tips for Google Stitch

1. **Run Master Design System first**, then each screen — consistency improves across generations.
2. **Regenerate** individual screens if charts or tables are illegible; ask Stitch to "increase text contrast and label all chart axes."
3. **Specify "desktop web app mockup, not mobile"** if outputs default to phone layouts.
4. **For case study decks:** export PNGs and pair with the screen names above.
5. **Brand note:** This is a PM research tool *about* Spotify feedback — not an official Spotify product. Avoid Spotify logo; use generic 🎧 + green accent only.

---

## Screen checklist

| # | Screen | Stitch prompt section |
|---|--------|----------------------|
| 1 | Executive Summary | Screen 1 |
| 2 | Source Analysis | Screen 2 |
| 3 | Discovery Challenges | Screen 3 |
| 4 | Theme Explorer | Screen 4 |
| 5 | Segment Explorer | Screen 5 |
| 6 | Root Cause Analysis | Screen 6 |
| 7 | Unmet Needs | Screen 7 |
| 8 | Discovery Journey | Screen 8 |
| 9 | Interview Validation | Screen 9 |
| 10 | Research Assistant | Screen 10 |
| — | Sidebar | Sidebar (shared) |
| — | Overview grid | Bonus |
