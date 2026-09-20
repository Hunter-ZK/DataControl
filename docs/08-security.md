# 08 · Security baseline

- Asset service is read-only from the portal perspective.
- No production asset data or credentials in git.
- No SQL execution or production-data preview.
- Model runtime must not receive DB credentials.
- Agent3 reads asset facts through internal portal APIs.
- Output is text/sanitized Markdown; never execute embedded HTML/script.
- Future auth phase: USER/ADMIN, JWT, service token and chat-session token.
