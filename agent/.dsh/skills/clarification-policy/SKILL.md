# clarification-policy
## Trigger
Activate when a governed metric, code value, time period or dimension is ambiguous or missing.
## Method
1. Call plan_metric; never infer a metric from table-name similarity.
2. When status is clarification_required, render exactly the returned option ids, labels, descriptions and values.
3. Ask about one missing decision at a time; offer a governed default only if supported by tool evidence.
4. Resume the original question in the same authenticated conversation after the user chooses.
5. If a cross-source join, DDL/DML, or full-table scan is requested, first describe the risk and seek explicit user approval to *generate* SQL.
## Answer
Use a structured single/multiple choice card where evidence permits; otherwise state what evidence is missing.
## Examples
Good: Two governed loan-balance metrics exist; display both, never choose silently.
Bad: Assume "贷款" always means the first available measure.
## Forbidden
Never fabricate options, code values, defaults, authorization, SQL execution or external knowledge.
