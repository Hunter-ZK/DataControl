# P2 Scope · Product UI

## Goal

Turn the P0/P1 validation shell into the formal DataControl product frontend without changing the read-only product boundary.

## Formal frontend stack

- Vue 3
- TypeScript
- Vite
- Vue Router
- Element Plus
- Axios
- Lucide SVG icon set

## Product pages

- Home search portal
- Asset search
- Asset catalog
- Data Overview
- Dataset detail
- Field detail
- Code-table list/detail
- Data-standard list/detail
- Word-root list/detail
- Metric list/detail
- Statistical-system list/detail
- Personal Center
- Development login

## Interaction rules

- real browser routes, history and direct links
- all non-home detail flows expose a natural return path
- stable `asset_id` remains the persisted identity
- technical names are visible but visually secondary to business definitions
- scheduling is part of dataset detail only
- no hidden model chain-of-thought
- no SQL execution

## Design direction

`Light Ocean × Calm SaaS × Data Tool`

The shell deliberately lowers navigation contrast, reduces heavy gradients/shadows, uses bounded centered content, professional vector icons, consistent tokens and responsive layouts. Search remains the primary entry point.

## P2/P3 boundary

P2 may display a lineage summary already provided by the backend, but graph/path/impact exploration belongs to P3. P2 exposes the intelligent-Q&A entry visually, but real dsh + Agent3 conversation belongs to P3.

## Platform baseline

Development and verification are supported on Windows and macOS. CI additionally validates Ubuntu. Node.js 24+ and Python 3.13+ are required for the formal P2 development environment.
