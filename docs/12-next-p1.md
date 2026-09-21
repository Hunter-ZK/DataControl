# Next-P1 · Search Correctness and Field Lineage

Status: active development

Frozen base: `3bc295f4b7d50fa4a4565cb3f698b551e2c3ee31` (Next-P0)

## Goal

Turn the existing P3 search/table-lineage prototype into a developer-first production interaction for locating assets and understanding table/field data flow.

## Deliverables

1. Search correctness
   - short Chinese terms work reliably;
   - multi-token queries are token-aware instead of forced exact phrases;
   - totals/facets describe the complete filtered result set, not a 500-row candidate window;
   - offset/limit pagination is first-class;
   - metadata enrichment is batched rather than N+1.
2. Relationship correctness
   - upstream and downstream traversal remain direction-pure;
   - `both` is the union of independent upstream/downstream traversals from the center and does not cross an ancestor into sibling branches.
3. Field-level lineage
   - persisted `rel_column_lineage` facts with source/target dataset and column identities;
   - transformation/expression, task name, evidence and relation type;
   - read-only API for field graph and table-scoped field edges;
   - deterministic synthetic corpus for acceptance.
4. Product UI
   - Search V2 segmented facets, pagination and Agent handoff;
   - Relation Graph V2 with a real SVG edge layer/arrows, evidence styling, asset picker and table/field modes;
   - dataset/field detail entry points into lineage.
5. Acceptance
   - backend regression coverage for short/multi-token search, complete facets/pagination, traversal direction and field lineage;
   - Vue type-check/tests/build;
   - existing P0/P3 gates remain green.

## Explicit non-goals

- semantic model V2 and advanced metric derivation (Next-P2);
- external research tools (Next-P2);
- real metadata staging/publish/versioning (Next-P3);
- production SQL execution (never enabled by this increment).
