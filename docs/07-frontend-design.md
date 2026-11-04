# 07 · Frontend design baseline

The supplied 9-screen prototype remains the information-architecture reference, but P2 is the formal product UI and is not a pixel copy.

## Visual direction

Design language: **Light Ocean × Calm SaaS × Data Tool**.

- very light ocean-blue / blue-grey application chrome
- white reading surfaces
- sea-blue accents for active state, action, focus and links
- restrained gradients and shadows; hierarchy relies primarily on spacing, type, border and surface contrast
- professional vector icon system rather than Unicode prototype glyphs
- technical identifiers use monospace treatment and never dominate business names/definitions
- consistent design tokens for radius, spacing, border, text hierarchy and shadows
- ODS/DWD/DWS/ADS/DIM layer semantics stay distinct from the brand palette
- keep the currently approved light-ocean visual language; targeted contrast and density improvements must not become a replacement design system

## App shell

- left-side primary navigation remains the stable module navigation
- full sidebar on wide desktop, icon rail on compact desktop, hidden sidebar on narrow viewports
- preserve the current sidebar, brand mark, active-state and topbar visual treatment
- top bar contains contextual breadcrumbs, compact global search/command entry and account controls
- consolidate navigation to Home, Asset Catalog, Data Standards, Metrics & Systems, Intelligent Q&A (P3 disabled placeholder) and Data Overview; Personal Center is reached from the account menu
- preserve all route paths and direct detail URLs
- all product pages use the same bounded centered content container
- no `margin-left + calc(width)` page compensation

## Home

Home is a search portal, not a dashboard.

Priority order:
1. preserve the existing hero proposition and prominent search field
2. keep common searches adjacent to the search field
3. remove repeated module-launcher cards already represented in the sidebar
4. show recent browsing and favorites as continuation workspaces
5. keep asset counts on the dedicated Data Overview page

## Search

- home search submits into `/search?q=...`
- non-home global search opens a command-style preview and can submit to the full `/search` results page
- search page contains result type tabs and results as the main work area
- result cards expose asset type, title, technical identifier and relevance score; show a hit excerpt only if the current API returns it
- the current P2 search API returns title highlighting but not a body excerpt, so the frontend must not fabricate a hit-context snippet; a true body excerpt requires a future API contract change
- result destinations are real routes for dataset/field/metric/code-table assets
- advanced ranking, server facets, typo correction and saved searches are P3 concerns

## Asset details

Dataset detail uses one consistent asset-detail hierarchy:
1. identity + lifecycle + necessary actions
2. compact metadata strip
3. content tabs
4. tags and optional additional information

Dataset detail includes basic definition, fields, common SQL, changes, lineage summary and **Scheduling & Operation**. Scheduling never becomes a standalone module. Avoid repeating the same identifier, definition, lifecycle state or update metadata in multiple panels.

Field routes remain valid but open the field drawer within the owning dataset workspace. Code tables, data standards, word roots, metrics and statistical systems retain their direct detail URLs and open the selected item in the relevant list/detail workspace.

## Responsiveness

Required verification widths include 1920, 1440, 1280, 1024, 820 and narrow browser widths. Technical names and data tables may scroll/truncate inside their component but must never create page-level horizontal overflow.

## Agent UI boundary

P2 may show the Intelligent Q&A entry as a disabled "即将上线" placeholder. Real dsh + Agent3 conversation is P3. Future Agent UI may show task/tool/provenance activity, never private chain-of-thought.
