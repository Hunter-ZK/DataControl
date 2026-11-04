# 02 · Product requirements V3 delta

The V2 information architecture remains the baseline with these approved changes:

1. Remove standalone **Scheduling Calendar** from navigation and scope.
2. Scheduling/operation metadata is displayed in **Dataset Detail > Scheduling & Operation**.
3. Dataset identity uses stable `asset_id`; table names may change without breaking favorites/history/audit/chat context.
4. P0/P1 do not build source metadata ingestion or governance.
5. Asset catalog defaults to all ONLINE assets; "Common only" is an optional filter.
6. Intelligent Q&A shows tool/activity summaries, never chain-of-thought.
7. Read-only Agent3 tools do not require repetitive user confirmation.
8. Existing 9-screen prototype defines information architecture, not final visual quality. Frontend implementation must refine hierarchy, spacing, density and interaction quality.
9. **Home is a search portal, not a dashboard.** Keep the existing light-ocean hero and prominent search interaction; remove repeated module-launcher cards and duplicate overview statistics. Use recent browsing and favorites as lightweight continuation.
10. Search preview/results must remain visually close to the search entry. The home search submits into `/search?q=...`; non-home pages use the global command search.
11. **Asset Overview is a separate page.** It contains the seven asset counts and the existing layer/domain distribution panels. The home page may only show lightweight recent/favorite continuation.
12. **Primary navigation remains on the left.** Keep the existing sidebar visual treatment; consolidate duplicate routes into six functional entries. The top bar uses breadcrumbs, global search and account controls.
13. P2 UI refinement must preserve the approved Light Ocean visual identity, existing card language, icon style and page composition except where a specific item below requires a targeted layout change.
14. Keep all existing routes and deep links valid when navigation entries are consolidated. Intelligent Q&A remains a disabled P3 placeholder until the Agent workflow is implemented.
15. Lists use in-page pagination based on the available viewport. Do not hide records to achieve a no-scroll appearance; narrow screens may use natural scrolling.
16. Displayed counts and pagination must reflect the full set currently returned by existing APIs. P2 UI refinement must not add backend endpoints or change backend data contracts.
