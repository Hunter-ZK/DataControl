# asset-explain
## Trigger
User asks what an asset means, where it comes from, or which objects reference it.
## Method
1. Resolve the asset via search_assets or an existing trusted assetId.
2. Get its detail with get_asset, including code/standard/metric definitions if available.
3. For referenced-by questions call find_references, and for upstream/downstream lineage use get_lineage_summary.
4. Identify whether each relationship is recorded in DataControl or is unknown.
## Answer
Business meaning → technical fields and governed definitions → references/lineage → caveats.
## Examples
Good: Show "not documented" when lineage is absent.
Bad: Infer source lineage merely from similar names.
## Forbidden
No synthetic dependency edges or unverified numeric values.
