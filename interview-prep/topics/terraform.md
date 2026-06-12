---
title: Terraform
bucket: tech
must: true
gap: false
rank: 2
sources: https://developer.hashicorp.com/terraform/docs
depth: standard
added: 2026-06-08
generated: true
---

## Core concepts

### Mechanism / internals

**State is the source of truth, not your cloud account.** Terraform writes a `terraform.tfstate` JSON document that maps each *configuration address* (e.g. `module.gw.aws_lb.this[0]`) to a *real resource ID* plus a cached snapshot of that resource's attributes ([State backends](https://developer.hashicorp.com/terraform/language/state/backends)). On `plan`, Terraform builds a resource graph, refreshes state against the providers' read APIs, and diffs *desired config* against *prior state* — it does **not** diff config against live reality directly; it diffs against what state *says* reality is, then reconciles. This is why state corruption or a stale state file produces wrong plans even when your HCL is correct.

**Plan vs apply, and saved plans.** `plan` produces an execution plan (an ordered set of create/update/replace/destroy actions). `apply` re-plans by default unless you feed it a *saved plan*: `terraform plan -out add-object` then `terraform apply "add-object"` ([Apply tutorial](https://developer.hashicorp.com/terraform/tutorials/cli/apply)). Saved plans are how you make CI gate the *exact* actions a human reviewed — the apply executes precisely those, with no re-evaluation drift between review and execution.

**Remote backends + locking.** The local backend stores a JSON file on disk; remote backends (S3, HCP Terraform, Consul, GCS) store it elsewhere and, critically, when non-local, "Terraform will not persist the state anywhere on disk except in the case of a non-recoverable error where writing the state to the backend failed" — so secrets in state never hit local disk ([Backends](https://developer.hashicorp.com/terraform/language/state/backends)). Locking serializes writes: the classic S3 pattern pairs the bucket with a DynamoDB table (`dynamodb_table = "terraform-state-lock-dynamo"`) so two concurrent applies can't interleave writes ([S3 backend](https://developer.hashicorp.com/terraform/tutorials/cloud/migrate-remote-s3-backend-hcp-terraform)). Without a lock, two applies refresh the same prior state, each computes a diff, and the second writes a state that has no record of the first's resources — orphaned infra and a corrupt state.

**count vs for_each addressing.** `count` indexes instances positionally: `aws_instance.a[0]`, `[1]`, `[2]`. `for_each` keys them by a map/set key: `aws_instance.a["small"]`. The address is the identity Terraform tracks in state.

### Trade-offs & when to choose

- **`for_each` over `count` for any list that can change in the middle.** Use `count` only for "nearly identical instances"; use `for_each` "when some instance arguments must have distinct values that can't be directly derived from an integer index" ([count](https://developer.hashicorp.com/terraform/language/meta-arguments/count)). Because `count` keys by position, deleting the *first* of three list items shifts `[1]→[0]` and `[2]→[1]`, so Terraform plans to destroy/recreate the survivors. `for_each` keys are stable, so removing one element touches only that element.
- **Workspaces vs directory separation.** Workspaces give you multiple states from *one* configuration (`terraform.tfstate.d/<name>/terraform.tfstate` for local; name appended to the path for remote — [Workspaces](https://developer.hashicorp.com/terraform/cli/workspaces)). They're cheap for transient/identical environments (dev/qa) but share the *same code and provider config*, so they're a poor fit for environments that diverge (different blast radius, different IAM, different provider versions). For prod isolation prefer separate directories/state files with their own backends.
- **Module composition.** Modules are the unit of reuse and the natural boundary for splitting state. Compose by passing explicit inputs/outputs; avoid deep nesting that makes the graph and blast radius hard to reason about.

### Failure modes / gotchas

- **count reorder = destroy on survivors** (above). The `moved` block fixes refactors without destruction: it rewrites state addresses during plan, e.g. `moved { from = aws_instance.a, to = aws_instance.a["small"] }` migrates a `count`/single resource into a `for_each` key with **0 destroys** ([refactoring](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring)).
- **Secrets in state.** State stores attribute values verbatim — DB passwords, private keys, generated secrets all land in plaintext JSON. `output ... sensitive = true` only redacts CLI display, not the stored value ([output block](https://developer.hashicorp.com/terraform/language/block/output)). Mitigation: a remote backend with encryption-at-rest + tight access (so state never touches local disk), and treating the state store as a secret store.
- **Drift.** Out-of-band changes (console edits, other tools) create drift. `plan`/refresh detect it by comparing live attributes to state; the fix is to re-apply (overwrite reality) or `import`/adjust config to adopt it. Drift is silent until the next plan.
- **`terraform import`: imperative CLI vs declarative block.** The CLI `terraform import addr id` mutates state immediately and out-of-band. The `import` block (`import { id = "...", to = aws_x.y }`) is plan/apply-driven and reviewable, and supports `-generate-config-out` to scaffold the matching `resource` block ([Import](https://developer.hashicorp.com/terraform/language/import)). Prefer import blocks at scale — they're idempotent, code-reviewed, and CI-friendly.
- **`removed` block.** Drops a resource from state *without destroying it* (Terraform 1.7+): `removed { from = aws_instance.x; lifecycle { destroy = false } }` — essential when handing a resource off to another state ([state CLI](https://developer.hashicorp.com/terraform/tutorials/state/state-cli)).

### Tuning / scale knobs

- **Split state to shrink blast radius.** One giant state means one lock, slow refreshes, and a single corrupting apply can damage everything. Split per service/region/layer; share read-only outputs via `terraform_remote_state` data sources or a registry. Smaller states = faster plans, narrower lock contention, smaller failure domain.
- **Provider/version pinning.** Pin Terraform (`required_version`) and providers (`required_providers { aws = { version = "~> 5.0" } }`) and commit `.terraform.lock.hcl`. Unpinned providers mean a fresh `init` can silently upgrade and change plan semantics. `~>` allows patch/minor within a floor; exact pins for high-stakes pipelines.
- **Idempotency & convergence.** A correct config converges: a no-op apply after a successful apply yields "0 to add, 0 to change, 0 to destroy." Perpetual diffs signal a provider bug, a normalization mismatch, or computed values you should mark `ignore_changes`.

## Interview questions

<details>
<summary><strong>Q:</strong> Two engineers run <code>terraform apply</code> against the same S3-backed state at the same time, and there's no lock. Walk through exactly how the state gets corrupted.</summary>

Both applies read the same prior state and refresh it, so each computes a diff relative to an identical starting point with no knowledge of the other. Engineer A creates resources and writes a new state; Engineer B, who started from the *old* state, then overwrites that state with its own result — which has no record of A's resources. A's infrastructure is now real but orphaned (unmanaged, invisible to future plans), and the state is internally inconsistent. The fix is a lock: the canonical S3 backend pairs the bucket with a DynamoDB table so the second apply blocks until the first releases the lock, serializing the read-modify-write. This is why remote backends with locking are non-negotiable for any shared state.

</details>

<details>
<summary><strong>Q:</strong> You have <code>count = length(var.subnets)</code> over three subnets and you delete the first one from the list. What does the plan show and why? How would you have avoided it?</summary>

`count` addresses instances by position, so the resources are tracked as `[0]`, `[1]`, `[2]`. Removing the first list element shifts everything down — old `[1]` is now `[0]`, old `[2]` is now `[1]` — so Terraform sees `[2]` no longer exists and the attributes at `[0]` and `[1]` changed identity, planning to destroy/recreate the survivors. The docs steer you to `count` only for "nearly identical instances" and to `for_each` when instances have distinct identity. With `for_each` over a map keyed by subnet name/CIDR, each instance has a stable key, so deleting one element destroys only that one and leaves the rest untouched. To migrate an existing `count` resource without destruction, add a `moved` block per key.

</details>

<details>
<summary><strong>Q:</strong> What does the state file actually store, and why is "config diffed against state" rather than "config diffed against the cloud" an important distinction?</summary>

State maps each configuration address to the real resource ID plus a cached snapshot of that resource's attributes. On plan, Terraform refreshes that snapshot against provider read APIs and then diffs *desired config* vs *prior state* — state is the source of truth for what Terraform believes it manages. The distinction matters because a stale, hand-edited, or corrupted state produces a wrong plan even with perfect HCL: Terraform will try to "fix" reality to match a state that's lying, or fail to see resources that exist but aren't in state. It's also why drift is invisible until a refresh, and why losing state is far worse than losing code — code you can rewrite, but state is the only record linking your config to live resource IDs.

</details>

<details>
<summary><strong>Q:</strong> Differentiate the <code>terraform import</code> CLI command from the <code>import</code> block. When would you reach for each at scale?</summary>

The CLI `terraform import <addr> <id>` mutates state immediately and imperatively — it's out-of-band, not reviewable, and not idempotent in a code-review sense. The `import` block (`import { id = "...", to = aws_x.y }`) is declarative and plan/apply-driven: it shows up in the plan, can be code-reviewed, runs in CI, and supports `-generate-config-out` to scaffold the matching resource block. At scale — importing dozens of existing resources, or adopting an org's pre-existing infra into Terraform — prefer import blocks: they're idempotent, batchable, and leave an audit trail. The CLI command is fine for a one-off interactive fix but doesn't belong in a pipeline.

</details>

<details>
<summary><strong>Q:</strong> Your CI runs <code>plan</code>, a human approves, then <code>apply</code> re-plans and does something different. How do you make the apply do exactly what was reviewed?</summary>

By default `apply` re-evaluates the plan, so anything that changed between review and execution — drift, a data source's value, a provider upgrade, someone else's apply — can alter what runs. Use a saved plan: `terraform plan -out tfplan` produces an immutable execution plan, and `terraform apply tfplan` executes precisely those actions with no re-planning. In CI you store the artifact between the plan and apply stages and gate human approval on it. This closes the time-of-check-to-time-of-use gap; the trade-off is that a saved plan can become stale (state moved on), in which case apply refuses it and you re-plan — which is the safe failure.

</details>

<details>
<summary><strong>Q:</strong> Secrets end up in state in plaintext. Walk through the real exposure and what actually mitigates it (and what doesn't).</summary>

State stores resource attributes verbatim, so generated passwords, private keys, RDS credentials, and provider-returned secrets all sit in the JSON. `output ... sensitive = true` only redacts the value in CLI output — it does **not** encrypt or remove it from state, so that's not a mitigation. What actually helps: a remote backend, because when non-local Terraform never persists state to local disk except on unrecoverable write failure, so the plaintext stays off laptops and CI runners. Then encrypt at rest (`encrypt = true` on S3 + KMS), lock down read access to the state store as if it were a secrets vault, and minimize secrets in state by sourcing them from a secrets manager at runtime where possible. The mental model: the state store *is* a secret store, govern it accordingly.

</details>

<details>
<summary><strong>Q:</strong> When would you use Terraform workspaces versus separate directories/backends for environments? Where do workspaces bite you?</summary>

Workspaces give multiple states from one configuration — local state lands in `terraform.tfstate.d/<name>/`, remote state appends the workspace name to the path. They're cheap for transient or genuinely identical environments (per-PR ephemeral stacks, dev/qa). They bite when environments diverge, because all workspaces share the *same code and provider configuration*: you can't easily give prod a different provider version, different IAM/backend, or a smaller blast radius, and a `terraform.workspace`-conditional sprinkled through the code gets fragile fast. For prod isolation I prefer separate directories with their own state and backend — independent locks, independent failure domains, and the freedom to evolve environments at different rates.

</details>

<details>
<summary><strong>Q:</strong> A resource shows a diff on every plan even though nobody changed anything. How do you diagnose perpetual drift?</summary>

A converged config should yield a no-op plan (0/0/0); a perpetual diff means desired, prior-state, and refreshed values disagree every time. Common causes: the provider normalizes a value differently than you wrote it (case, ordering, default injection), a computed/server-side field you're trying to set, or an attribute another system mutates out-of-band. Diagnose by reading the exact `~` lines in the plan to see *which* attribute flaps, then check the provider docs for normalization, and `terraform state show` to compare stored vs live. Fixes: write the value in the provider's canonical form, move server-managed fields out of config, or `lifecycle { ignore_changes = [...] }` for legitimately externally-managed attributes — used surgically, not as a blanket suppressant.

</details>

<details>
<summary><strong>Q:</strong> You're refactoring a flat config into modules and renaming resources. How do you do it without destroying live infrastructure?</summary>

Renaming or moving a resource changes its configuration address, and since the address is the identity in state, a naive change makes Terraform plan to destroy the old address and create the new one. Use `moved` blocks: they rewrite the state address during plan, so `moved { from = aws_instance.example, to = module.ec2_instance.aws_instance.example }` shows the resource "has moved" with 0 destroys. The same mechanism migrates `count` to `for_each` one key at a time. `moved` blocks are declarative and reviewable — preferable to imperative `terraform state mv`, which is out-of-band and easy to fat-finger. Verify by confirming the plan reports moves and updates, never destroy/create, before applying.

</details>

<details>
<summary><strong>Q:</strong> Design the state layout for a platform deployed across ~30 regions with multiple services per region. What are your splitting principles and the trade-offs?</summary>

Never one monolithic state — it means a single lock (serializing every team), slow whole-fleet refreshes, and a blast radius where one bad apply can damage everything. Split along axes that match failure domains and ownership: per-region and per-service-layer (network → platform → app), so a region's plan touches only that region's state. Share cross-cut data read-only via `terraform_remote_state` or published module outputs rather than coupling states. Pin providers and commit the lock file per state so regions can roll versions independently in phases. The trade-off is more states to orchestrate and a dependency graph between them you must sequence (the network layer must apply before the app layer); you manage that with a thin orchestration layer and clear output contracts, accepting that explicitness in exchange for narrow blast radius and parallelizable applies.

</details>

<details>
<summary><strong>Q:</strong> Why pin provider versions and commit the lock file? What goes wrong if you don't?</summary>

Set `required_version` for Terraform and `required_providers { aws = { version = "~> 5.0" } }` for providers, and commit `.terraform.lock.hcl`. Without pinning, a fresh `terraform init` resolves the newest matching provider, which can change plan semantics — a provider upgrade may add new required defaults, change normalization, or alter how an attribute maps — so the same code produces a different plan on a different machine or a later day. The lock file records the exact selected versions and their checksums so init is reproducible across CI and every engineer's laptop, which also protects against a tampered provider. For high-stakes pipelines I pin tighter (exact or narrow `~>`) and bump deliberately; loose constraints are fine for low-risk modules.

</details>

<details>
<summary><strong>Q:</strong> You need to hand a resource off from one state to another (state-splitting) without any downtime. How?</summary>

In the source config, use a `removed` block with `lifecycle { destroy = false }` so Terraform drops the resource from state *without* destroying the live resource (Terraform 1.7+). In the destination config, add an `import` block referencing the same real resource ID and a matching `resource` block, so the new state adopts it on apply. Sequence: apply the `removed` in the source first (resource now unmanaged but alive), then apply the `import` in the destination. The live resource never stops; only the ownership in state changes. The older imperative equivalent is `terraform state rm` + `terraform import`, but the block-based flow is reviewable and CI-safe, which matters when you're doing this across many resources or regions.

</details>

<details>
<summary><strong>Q (resume):</strong> You cut new-region/new-realm build from 30 days to 8 hours with Terraform. What was the actual bottleneck and what did the IaC change structurally?</summary>

The 30 days was almost entirely ticket-driven cross-team dependencies — provisioning steps that waited on humans to action requests serially. Replacing that with Terraform-based automation turned those dependencies into code: policy serialization and tenancy-aware provisioning became declarative resources with explicit graph dependencies, so Terraform sequenced them automatically instead of a human shepherding tickets between teams. The structural win is idempotent, repeatable convergence — a new region is "apply this config against a new tenancy" rather than re-running a runbook — which is also what makes it safe to repeat across 34 regions. The 8 hours is mostly real provider wait time (resources actually being created), not coordination latency, which is the irreducible floor once the human serialization is gone.

</details>

<details>
<summary><strong>Q (resume):</strong> Rolling an ARM change across 34 production regions in 4 phases — how did Terraform's state and module model support staged rollout and limit blast radius?</summary>

Per-region (or per-phase) state separation is what makes a phased rollout possible: each region has its own state and lock, so phase 1 regions can apply, bake, and be validated before phase 2 touches anything, and a failure is contained to that region's failure domain rather than the whole fleet. A shared module encodes the region build once so all 34 regions are the *same* code parameterized by region inputs, which keeps them consistent while letting provider/version pins advance per phase via committed lock files. The phasing itself is an orchestration layer over independent states — plan-and-apply each cohort, gate on health, proceed — and saved plans let each cohort's change be reviewed and applied exactly as approved, which is the guardrail you want when 34 production regions are downstream.

</details>

## Say it with your resume

- **Lead: 30 days to 8 hours.** Replaced ticket-driven, human-serialized provisioning with Terraform-based automation for new-region/new-realm builds on OCI API Gateway — the dependency graph that humans used to shepherd between teams became declarative resources Terraform sequences automatically, collapsing coordination latency to near-zero and leaving only real provider wait time.
- **Idempotent, tenancy-aware provisioning.** Streamlined policy serialization and tenancy-aware provisioning into repeatable Terraform config, so standing up a new region is "apply against a new tenancy" with convergent, no-op-on-rerun behavior — the property that makes repeating it across 34 regions safe.
- **34-region ARM rollout in 4 phases.** Used per-region state separation (independent locks, independent failure domains) plus a shared parameterized module so each phase could apply, validate, and bake before the next — limiting blast radius and keeping all regions on identical, version-pinned code.
- **State-tier reduction 68.4%.** Drove down state-tier footprint, consistent with disciplined state splitting and lifecycle hygiene rather than one monolithic state — faster plans, narrower lock contention, smaller corruption surface.
- **Sequenced live migration with guardrails.** The 8-step Redis live-migration (sequencing, health-checks, guardrails) is the same staged, gated, health-validated rollout discipline applied at the data tier — the human-facing analog of plan-review-apply with saved plans.

## Sources

- [Terraform docs](https://developer.hashicorp.com/terraform/docs)
- [State and backends](https://developer.hashicorp.com/terraform/language/state/backends)
- [S3 remote backend with DynamoDB locking](https://developer.hashicorp.com/terraform/tutorials/cloud/migrate-remote-s3-backend-hcp-terraform)
- [Workspaces](https://developer.hashicorp.com/terraform/cli/workspaces)
- [count meta-argument](https://developer.hashicorp.com/terraform/language/meta-arguments/count)
- [Refactoring with moved blocks](https://developer.hashicorp.com/terraform/language/modules/develop/refactoring)
- [Import](https://developer.hashicorp.com/terraform/language/import)
- [Saved plans / apply tutorial](https://developer.hashicorp.com/terraform/tutorials/cli/apply)
- [output block (sensitive)](https://developer.hashicorp.com/terraform/language/block/output)
- [State CLI / removed block](https://developer.hashicorp.com/terraform/tutorials/state/state-cli)
