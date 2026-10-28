# sql-revision
## Trigger
User says "改成同比", "只看广东", "换维度", or requests a follow-up to a governed SQL query.
## Method
1. Prefer the last *validated semanticPlan* in the authenticated conversation, not prior SQL text.
2. Call revise_query with the precise, declarative modifications only.
3. Preserve original metric IDs, mandatory filters, and permitted dimensions.
4. Compile and validate the revised QueryIR; fail closed on conflicts.
5. Show what changed from the previous plan in one sentence.
## Answer
Changes → validated SQL → source metric and basis → caveats.
## Examples
Good: Add a governed filter while retaining the metric's required constraints.
Bad: Rewrite SQL text manually and assume the old validation is still valid.
## Forbidden
Never pass raw WHERE SQL, silently change metric definitions or reuse an old validation badge.
