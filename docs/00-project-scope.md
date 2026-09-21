# 00 · Project scope

DataControl is the complete product repository for the data-asset portal and its DataAgent capability.

## In scope

- asset browsing and display;
- unified asset search;
- standards, code tables, word roots, metrics and statistical systems;
- relationship/lineage guidance, path finding and impact analysis;
- intelligent Q&A and trusted SQL generation/validation;
- user/application data such as favorites, recent views and search history;
- self-contained Windows/macOS developer startup and CI.

## Repository ownership

The final product is delivered from `Hunter-ZK/DataControl` only:

```text
web/       product UI
backend/   Portal services
agent/     embedded DataAgent subsystem
```

`Hunter-ZK/DataAgent-dsh` is the P3 migration baseline for `agent/`, pinned at commit `f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`. It is not a second repository that users must clone or deploy. `Hunter-ZK/Agent3.0` is historical/reference material only.

## Explicitly out of current V1 scope

- production SQL execution;
- write-back governance workflows;
- DataWorks/MaxCompute automatic metadata synchronization;
- standalone scheduling operations/monitoring center;
- production SSO/LDAP and final enterprise security hardening before P4;
- mobile/i18n/Kubernetes delivery unless later approved.

DataControl may contain multiple local processes, but they are started and versioned from the one repository.
