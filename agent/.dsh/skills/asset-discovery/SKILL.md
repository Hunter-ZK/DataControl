# asset-discovery
## Trigger
User asks to find tables, fields, metrics, code tables, word roots, standards or statistical systems.
## Method
1. Use search_assets with the original business phrase.
2. Rank by exact technical code/name match, then relevant description and asset type.
3. Call get_asset only for shortlisted IDs to verify detail and relationship.
4. If ambiguous, present multiple grounded options rather than guessing.
## Answer
Asset title, technical name, asset type, stable assetId, relevant use, direct asset link.
## Examples
Good: Find both metric and source table when user types "贷款余额".
Bad: Treat an arbitrary first table match as the indicator's defined source.
## Forbidden
Do not fabricate an assetId, invent a relationship or browse outside DataControl.
