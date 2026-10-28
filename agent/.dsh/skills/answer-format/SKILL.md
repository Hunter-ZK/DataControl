# answer-format
## Trigger
Use for any completed DataControl business or SQL answer.
## Method
1. Summarize the supported conclusion in one short sentence.
2. Reference actual metric/asset evidence returned by MCP; let the frontend render cards from structured tool results.
3. If SQL exists, provide the exact validated SQL only once, with validation status and caveats.
4. Offer one relevant optional follow-up based on actual available dimensions/filters.
5. Show evidence gap or unresolved ambiguity instead of asserting success.
## Answer
Conclusion → evidence/asset references → SQL and validation (when relevant) → one next action.
## Examples
Good: "已生成贷款余额 SQL，静态验证通过；未执行查询。"
Bad: "贷款余额为 100 亿元" without execution or sourced result.
## Forbidden
Never invent execution, asset IDs, citations, hidden reasoning, or facts.
