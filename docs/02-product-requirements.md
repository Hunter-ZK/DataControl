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
9. **Home is a search portal, not a dashboard.** The first screen contains one dominant global search box, common searches, recent work and a lightweight asset-overview continuation. Persistent module navigation stays in the left sidebar instead of being duplicated as home-page launcher cards; sidebar hover guidance may explain each module.
10. Search preview/results must be visually adjacent to the search box. Typing and result feedback form one interaction block rather than being separated by dashboard content.
11. **Asset Overview is a separate page.** It contains asset counts, layer/domain distribution and recent asset changes. The home page may only show very lightweight continuation/recent-work content.
12. **Primary navigation remains on the left.** The top bar is reserved for breadcrumb/page title, compact global search, Agent shortcut and user/system controls. Pure top navigation is not used because the product has too many persistent tool modules and must remain extensible.


## Approved UX direction — 2026-10-20

13. **Primary navigation uses a compact top pill bar.** The persistent left sidebar is removed. Primary destinations are Home, Data Assets, Relationship Analysis, Standards, and Asset Overview. Profile remains under the top-right avatar.
14. **DataAgent is embedded in Home as the primary work surface.** Users ask asset questions, request Text2SQL, and obtain naming guidance without first navigating to a standalone chat page. The full conversation route remains a secondary history/evidence workspace.
15. **AI has a dedicated semantic color.** Neutral black/white/grey surfaces carry product structure; purple identifies DataAgent-generated actions, recommendations and evidence; orange/red indicate warnings and risk; green indicates healthy/ready states.
16. **Analytical answers prefer structured visual components over prose-only chat.** Asset recommendation uses relationship/network views, trend questions use charts, Text2SQL exposes semantic planning plus SQL validation, and naming assistance exposes word-root decomposition and reuse guidance.
17. **Demo fixtures are allowed only as visibly labeled preview data** when live Agent or product data is unavailable. Demo values must never be presented as production facts.
