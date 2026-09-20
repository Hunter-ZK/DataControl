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
9. **Home is a search portal, not a dashboard.** The first screen contains one dominant global search box, immediate search feedback, and 4–6 module launchers such as Asset Catalog, Standards/Code Tables, Word Roots, Metrics/Statistical Systems and Intelligent Q&A.
10. Search preview/results must be visually adjacent to the search box. Typing and result feedback form one interaction block rather than being separated by dashboard content.
11. **Asset Overview is a separate page.** It contains asset counts, layer/domain distribution and recent asset changes. The home page may only show very lightweight continuation/recent-work content.
12. **Primary navigation remains on the left.** The top bar is reserved for breadcrumb/page title, compact global search, Agent shortcut and user/system controls. Pure top navigation is not used because the product has too many persistent tool modules and must remain extensible.
