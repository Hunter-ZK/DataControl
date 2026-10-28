# dq-testing
## Trigger
User requests data validation, reconciliation checks or test cases for a warehouse dataset.
## Method
1. Identify known columns, primary grain, code domains and governed metrics.
2. Call generate_dq_checks for deterministic non-destructive read-only checks. Where a period field is documented, use `'${dt}'`; never infer the maximum partition.
3. Explain each check's purpose, expected zero/threshold criteria and limitations.
4. Validate generated statements; any simulated execution is evaluation-only and outside the production Agent.
## Answer
Rule table → SQL drafts → expected results → exceptions and evidence.
## Examples
Good: Compare key counts, nulls and valid code domains on documented fields.
Bad: Assume every table has an 'id' primary key or a known valid range.
## Forbidden
No production execution, destructive DML or fictional test outcomes.
