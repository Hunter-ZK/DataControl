# 07 · Frontend design baseline

The supplied 9-screen prototype remains the information-architecture reference. P0 raises the visual baseline rather than pixel-copying it.

## Visual direction
- Use a **light ocean-blue** visual system: blue-tinted near-white backgrounds, white surfaces, soft cyan/sea-blue accents and restrained deep blue for navigation.
- The product should feel younger and lighter than a traditional enterprise admin console while remaining professional and information-dense.
- Avoid flooding the page with blue. White remains the primary reading surface; ocean blue is used for hierarchy, active state, focus, links and subtle atmosphere.
- Reduce card-wall effect: use whitespace, typography and separators before borders.
- Technical identifiers use monospace treatment.
- ODS/DWD/DWS/ADS/DIM preserve stable layer colors independent of the brand palette.

## Navigation
- Keep the **left-side primary navigation** for stable module discovery and future expansion.
- Use the top bar only for breadcrumb/page title, compact global search, Agent shortcut and user/system controls.
- Add **Data Overview** as a separate secondary navigation item rather than making the home screen a dashboard.

## Home / search portal
- Search is the dominant first-screen action.
- Home is a search portal: one large search field, immediate suggestions/results directly below it, then 4–6 module launchers.
- Recommended launchers: Asset Catalog, Standards & Code Tables, Word Roots, Metrics & Statistical Systems, Intelligent Q&A. Relation Explorer can remain in persistent left navigation rather than compete for first-screen space.
- Module launchers use icon + name + one-line explanation; do not use icon-only app-launcher patterns.
- Only lightweight recent-work content may appear below the launchers. Asset counts, business distribution and monitoring-style statistics belong on Data Overview.

## Data overview
- A separate Data Overview page contains asset counts, layer/domain distribution, asset status and recent changes.
- It is an analytical/supporting page, not the default landing page.

## Dataset detail
- Dataset detail must answer in 3 seconds: what it is, whether usable, owner, freshness, where to trace/ask.
- Dense pages use progressive disclosure and inspector panels.
- Scheduling is part of Dataset Detail > Scheduling & Operation; there is no standalone scheduling-calendar module.

## Agent UI
- Agent UI exposes activity/tool summaries, not private reasoning.

## P0 prototype
`web/prototype/index.html` now contains three reference states: search-portal home, standalone Data Overview and Dataset Detail. The search preview is docked immediately below the large search field and is backed by the synthetic search API when the backend is running.
