# task-planning
## Trigger
Only multi-step warehouse authoring and cross-asset tasks that cannot be resolved in one governed query.
## Method
1. State deliverables and steps, with expected evidence and validation for each.
2. Use dsh-native plan/todo facilities; keep shell, filesystem and network tools disabled.
3. Seek user confirmation before generating risky SQL proposals.
4. Call only approved Agent3 MCP tools for business facts.
5. Mark each step complete only after verifying its actual output.
## Answer
Readable task plan → step outcomes → generated artifacts → unresolved risks.
## Examples
Good: Verify source dataset and grain before generating ETL.
Bad: Claim a DDL was deployed or any production query executed.
## Forbidden
No unapproved execution, production modification, fake logs or fabricated plan progress.
