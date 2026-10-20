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

## App shell

- left-side primary navigation remains the stable module navigation
- full sidebar on wide desktop, icon rail on compact desktop, hidden sidebar on narrow viewports
- top bar contains current page, browser-level back affordance, compact global search/command entry and user actions
- all product pages use the same bounded centered content container
- no `margin-left + calc(width)` page compensation

## Home

Home is a search portal, not a dashboard.

Priority order:
1. search proposition and large search field
2. common searches
3. module launchers
4. recent work
5. only a lightweight asset overview entry

Primary launchers:
- Asset Catalog
- Standards & Code Tables
- Word Roots
- Metrics & Statistical Systems
- Intelligent Q&A

## Search

- home search submits into `/search?q=...`
- search page contains only facets + results as the main work area
- result cards expose asset type, business name, technical identifier, hit context and score
- result destinations are real routes for dataset/field/metric/code-table assets
- advanced ranking, server facets, typo correction and saved searches are P3 concerns

## Asset details

Dataset detail uses one consistent asset-detail hierarchy:
1. identity + lifecycle + actions
2. compact metadata strip
3. content tabs
4. related/identity side widgets

Dataset detail includes basic definition, fields, common SQL, changes, lineage summary and **Scheduling & Operation**. Scheduling never becomes a standalone module.

Fields, code tables, data standards, word roots, metrics and statistical systems expose dedicated detail routes where the current P2 data model supports them.

## Responsiveness

Required verification widths include 1920, 1440, 1280, 1024, 820 and narrow browser widths. Technical names and data tables may scroll/truncate inside their component but must never create page-level horizontal overflow.

## Agent UI boundary

P2 may show the Intelligent Q&A entry. Real dsh + Agent3 conversation is P3. Future Agent UI may show task/tool/provenance activity, never private chain-of-thought.
