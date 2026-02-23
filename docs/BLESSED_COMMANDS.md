# Blessed Runtime Commands

The runtime command interface is the personal `w` CLI. Workbench does not expose
top-level executable wrappers.

Current blessed commands:
- `w backup project`
- `w backup secrets`
- `w backup snapshot`
- `w vault create-project`
- `w ingest external`
- `w ingest vault`
- `w split files`
- `w split write`
- `w split select-records`
- `w split select-sentinel`
- `w split smoke`

Rules:
- If a blessed command exists, use it through `w`.
- If a pipeline is used repeatedly, add a thin `w` subcommand that delegates into Workbench.
