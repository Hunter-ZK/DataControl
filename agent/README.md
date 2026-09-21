# DataControl Agent subsystem

`agent/` is the permanent home of DataControl's DataAgent capability. The final product is a **self-contained monorepo**: users clone `Hunter-ZK/DataControl` and must not need a second Git repository at runtime.

## Source baseline

The migration source is `Hunter-ZK/DataAgent-dsh` `main` at commit:

`f04e266c6fe93e6e89d7e4b5c6e31128082a8c96`

That repository already contains the intended architecture: DeepSeek Harness as a replaceable Agent Runtime, thin MCP/HTTP/CLI adapters, and a harness-agnostic Agent3 Core. It is a **migration baseline/reference**, not a deployment dependency.

The old `Hunter-ZK/Agent3.0` repository is historical/reference material only and is not the DataControl integration target.

## Frozen dependency direction

```text
DataControl Vue
  -> Portal FastAPI
  -> Agent Gateway
  -> agent/ local DataAgent runtime
       -> dsh Agent Loop
       -> MCP Adapter
       -> Agent3 Core
            -> Metadata / Semantic / SQL / Policy
```

Portal and Agent remain separate code/runtime boundaries even though they live in one Git repository. Portal must not import Agent3 Core directly. Agent Core must not import Portal modules.

## Migration scope

Migrate from DataAgent-dsh only the assets required by the product runtime:

- `src/agent3` Core and adapters;
- `.dsh/skills`;
- dsh pinned runtime/profile/preset assets;
- guard plugin;
- semantic model assets;
- architecture/security tests needed to preserve boundaries.

Do not migrate historical Git data, private datasets, private benchmarks, old repository-only migration notes, credentials, or generated runtime state.

## Runtime rules

- DataControl runtime must not `git clone`, import from, or shell into `DataAgent-dsh`.
- dsh owns the open-ended agent loop; Portal does not reimplement it.
- MCP remains a thin adapter, not business Core.
- SQL generation/validation is allowed; production SQL execution is not.
- Hidden model reasoning is never surfaced to the Portal.
- Unexpected write/approval surfaces are denied unless a later explicitly approved product scope changes this rule.

During P3 migration `runtime-manifest.json` remains `integrated: false`; the Portal intentionally reports Agent unavailable instead of faking successful integration. It becomes `true` only after the embedded source, startup scripts, tests and local end-to-end path all pass.
