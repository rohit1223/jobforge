---
title: CI/CD & Pipelines
bucket: tech
must: true
rank: 4
sources: https://www.jenkins.io/doc/
depth: standard
added: 2026-06-08
generated: true
---

## Core concepts

### Mechanism

**Pipeline-as-code.** A pipeline is versioned alongside the application as a `Jenkinsfile` so the build/test/deploy contract is reviewable, diffable, and rollback-able like any other code. Jenkins offers two flavours. **Declarative** is a constrained, opinionated structure (`pipeline { agent; stages; steps }`) with first-class `post`, `when`, `environment`, `options`, and `parallel` blocks — the engine validates the whole file up front, so you fail fast on syntax. **Scripted** is full Groovy on a `node {}` block: arbitrary control flow, `try/finally`, library calls — more power, no guardrails, harder to lint. Practical senior stance: declarative for 90% of pipelines (readability, validation, shared-library discipline), drop to scripted only for genuinely dynamic graphs, and push complexity into `vars/` of a Shared Library rather than fattening the `Jenkinsfile`.

**Agents and executors.** `agent` declares *where* a stage runs; an **executor** is one concurrent build slot on a node. `agent any` runs on the controller's available executor (bad for isolation); `agent { label 'linux && jdk21' }` schedules onto a matching node; `agent { docker { image '...' } }` runs the stage inside a container so the toolchain is pinned and ephemeral. The controller should run *zero* build executors — it only schedules. Per-stage agents let you fan a `parallel` block across heterogeneous nodes.

**Artifacts vs caching.** These solve different problems. **Artifacts** are *outputs you must retain* — the built jar, test reports, an SBOM — captured with `archiveArtifacts artifacts: '...', fingerprint: true` (fingerprinting lets Jenkins trace which build produced which file across jobs), or passed *within* a run via `stash`/`unstash`. **Caching** is a *performance optimization for inputs* — `~/.m2`, `~/.gradle`, npm/pip caches — that must never change the output. The failure mode is conflating them: caching build outputs poisons reproducibility; treating a cache as authoritative hides "works because of a stale cache" bugs.

```groovy
pipeline {
  agent none
  options { timeout(time: 30, unit: 'MINUTES'); disableConcurrentBuilds() }
  stages {
    stage('Build') {
      agent { docker { image 'eclipse-temurin:21-jdk' } }
      steps { sh './gradlew build' }
      post { success { stash name: 'app', includes: 'build/libs/*.jar' } }
    }
    stage('Test') {
      parallel {
        stage('unit')        { agent { label 'linux' } steps { sh './gradlew test' } }
        stage('integration') { agent { label 'linux' } steps { sh './gradlew it' } }
      }
      post { always { junit 'build/reports/**/*.xml'; archiveArtifacts 'build/libs/*.jar' } }
    }
  }
}
```

### Trade-offs (deployment strategies)

| Strategy | Mechanism | Rollback | Cost / risk profile |
|---|---|---|---|
| **Rolling** | Replace instances in batches; old + new coexist briefly | Roll *forward/back* batch by batch — slow, no instant cutover | Cheapest (no duplicate fleet); but two versions serve traffic at once, so schema/API must be backward-compatible |
| **Blue-green** | Two identical fleets; flip the router from blue→green atomically | Near-instant: flip the router back | ~2x infra during cutover; **all** users move at once, so blast radius is 100% until you trust green |
| **Canary** | Route a small % to new version, watch SLOs, ramp | Stop the ramp / shift traffic back; smallest blast radius | Most operationally complex: needs traffic-shaping, real-time metrics, automated analysis |

**Progressive delivery** generalizes canary: deploy decoupled from release. **Feature flags** ship code dark and flip exposure at runtime per cohort, so a "deploy" is no longer the risky event — the flag flip is, and it's reversible in seconds without a rebuild. The senior insight: *blue-green derisks the infrastructure swap, canary/flags derisk the behaviour change* — they compose. And the rule that matters in an incident: **automate rollback, not just deploy** — if rollback is a manual runbook it's slow, and slow rollback makes teams deploy less, which makes each deploy bigger and riskier.

**GitOps / pull vs push.** Push deploys have the pipeline hold cluster credentials and `kubectl apply` outward — simple, but CI now has prod write access and drift is invisible. Pull/GitOps (Argo CD, Flux) makes Git the desired-state source of truth; an in-cluster agent reconciles continuously, so the audit trail is the commit log, rollback is `git revert`, and CI never holds cluster creds. Trade-off: another control plane to run, and "the cluster reconciled but the app is unhealthy" needs separate health gating.

### Failure modes / gotchas

- **Secrets leaking in logs.** Jenkins masks credentials bound via `credentials()` / `withCredentials`, but masking is *string matching on the env var value*. The classic leak: Groovy-interpolating a secret into a `sh` step with double quotes — `sh """curl -H 'Token: $TOKEN'..."""` — interpolates the value into the command *before* the shell runs, so it lands in the process table and can defeat masking. Correct: single-quote the script and let the **shell** expand `${TOKEN}`: `sh 'curl -H "Authorization: Bearer ${TOKEN}"...'`. Also `set +x` before secret-bearing commands to keep the shell from echoing them.
- **Non-hermetic builds.** Pulling `latest` tags, unpinned dependencies, network access during build, or reading host state makes "it built yesterday" non-reproducible. Pin base images by digest, lock dependency versions, and run in clean ephemeral containers.
- **Flaky tests.** A test that passes/fails non-deterministically destroys signal — engineers learn to "just re-run", which hides real regressions. Quarantine flakes out of the gating path, track them as bugs, never blanket-retry the whole suite to green.
- **Caching poisoning reproducibility** (see above) and **`agent any` on the controller** leaking workspace/secret state into the scheduler.

### Tuning / reliability knobs

- **Pipeline durability / reliability:** `options { timeout(...) }` per pipeline and stage so a hung deploy can't pin an executor forever; `retry(n)` only around genuinely idempotent network steps (never around tests — that masks flakes); `disableConcurrentBuilds()` for deploy jobs that mutate shared state.
- **Throughput:** size executors to CPU, fan work out with `parallel` + labelled agents, prefer ephemeral container/k8s agents over snowflake static nodes.
- **Test pyramid in CI:** many fast unit tests gating every commit, fewer integration tests, very few slow end-to-end tests — run the cheap layers first and `failFast` so a broken unit test doesn't burn an hour of E2E.
- **Supply-chain (SLSA):** SLSA's build track L1→L3 raises assurance — L1 just requires provenance to exist; **L2 requires the provenance be generated by the build *service*, not the build script** (so a compromised script can't forge it); **L3 adds build isolation and protects the provenance-signing key from user build steps**. Practically: pin/digest dependencies, generate an SBOM, and **sign** artifacts (e.g. cosign) so consumers can verify what your pipeline produced.

## Interview questions

<details>
<summary><strong>Q:</strong> Declarative vs scripted Jenkins pipelines — when do you reach for each, and where does complexity actually belong?</summary>

Senior model answer: Declarative gives a validated, opinionated structure with first-class `post`/`when`/`parallel`/`options`, so the whole file is parsed and rejected up front — that fail-fast and readability is why it's my default. Scripted is full Groovy on a `node {}` block: arbitrary control flow and `try/finally`, which I only use for genuinely dynamic stage graphs that declarative can't express. The key discipline is that *neither* should get fat — I push reusable logic into a Shared Library (`vars/`) so the `Jenkinsfile` stays a thin, reviewable contract and 50 repos share one tested deploy step. Cramming Groovy into the `Jenkinsfile` is the anti-pattern: it's untested, un-linted, and copy-pasted across jobs.

</details>

<details>
<summary><strong>Q:</strong> Explain the difference between artifacts, stash/unstash, and caching. What breaks if you confuse them?</summary>

Senior model answer: Artifacts are outputs you must *retain* across the build's life — the jar, test XML, SBOM — captured with `archiveArtifacts` plus `fingerprint: true` so Jenkins can trace which build produced which file. `stash`/`unstash` passes files *between stages within one run* (e.g. build output to a deploy stage on another node), and is ephemeral. Caching is purely an input-side speed optimization for `~/.m2`, npm, etc. The failure mode is caching *outputs* or treating a cache as authoritative: you get "it only builds because of a stale cache" bugs that vanish on a clean agent and silently break reproducibility. Rule of thumb: a cache must be safe to delete at any time without changing the result.

</details>

<details>
<summary><strong>Q:</strong> Compare rolling, blue-green, and canary deployments on rollback speed, blast radius, and cost.</summary>

Senior model answer: Rolling replaces instances in batches — cheapest (no duplicate fleet) but two versions serve traffic simultaneously, so it demands backward-compatible schemas/APIs and rollback is a slow reverse-roll. Blue-green stands up a second identical fleet and flips the router atomically: near-instant rollback (flip back) and clean isolation, at ~2x infra during cutover and 100% blast radius the instant you flip. Canary routes a small percentage to the new version, watches SLOs, and ramps — smallest blast radius and best for behaviour risk, but it needs traffic-shaping and real-time metric analysis, so it's the most operationally complex. They compose: blue-green derisks the infra swap, canary/flags derisk the behaviour. I pick based on risk tolerance, infra budget, and required recovery speed.

</details>

<details>
<summary><strong>Q:</strong> A deploy broke prod at 2am. How does your pipeline prevent or limit that, and how do you get back to green fast?</summary>

Senior model answer: Limiting blast radius is the design goal: I deploy via canary or behind a feature flag so only a cohort sees the change, with automated SLO analysis that halts and reverts the ramp if error rate or latency breaches budget — so the "bad deploy" never reaches everyone. The recovery rule is *automate rollback, not just deploy*: a one-click/automatic revert (router flip for blue-green, flag off for progressive, `git revert` for GitOps) means recovery is seconds, not a manual runbook. Pre-merge gates (test pyramid, integration checks) and post-deploy health gates catch most of it earlier. And I separate deploy from release with flags so the on-call fix is flipping a flag, not rebuilding and redeploying under pressure.

</details>

<details>
<summary><strong>Q:</strong> How does Jenkins mask secrets, and what's the exact way teams still leak them into build logs?</summary>

Senior model answer: Jenkins masks credentials bound through `credentials()` or `withCredentials` by string-matching the secret's value in console output — but masking is fragile because it's just substitution. The classic leak is Groovy string interpolation: writing `sh """curl -H 'Token: $TOKEN'..."""` makes *Groovy* substitute the value into the command string before the shell ever runs, so the secret ends up in the process table and can dodge masking. The fix is to single-quote the `sh` body so the value never enters Groovy's string, and let the shell expand it: `sh 'curl -H "Authorization: Bearer ${TOKEN}"...'`. I also `set +x` around secret-bearing commands so the shell doesn't echo them, and prefer short-lived/OIDC tokens so a leak has a tiny window.

</details>

<details>
<summary><strong>Q:</strong> What makes a build hermetic/reproducible, and why does it matter for security as well as debugging?</summary>

Senior model answer: A hermetic build depends only on explicitly declared, pinned inputs and nothing from the host or network at build time — same inputs, same bytes out. Concretely: pin base images by digest (not `latest`), lock dependency versions, run in clean ephemeral containers, and avoid reading ambient host state. It matters for debugging because "it built yesterday" stops being a mystery — you can rebuild any historical commit identically. For security it's foundational to supply-chain trust: if the build isn't deterministic you can't meaningfully attest provenance or do reproducible-build verification, and an unpinned dependency is an open door for a poisoned upstream package.

</details>

<details>
<summary><strong>Q:</strong> Walk me through SLSA build levels and what each one actually buys you.</summary>

Senior model answer: SLSA's build track is cumulative, L0→L3. L1 just requires that provenance *exists* — a record of how and where the artifact was built — which gives basic traceability. L2 raises the bar by requiring the provenance be generated by the build *service*, not the user's build script, and signed — so an attacker who compromises the build script can't forge provenance. L3 adds platform hardening: isolation so one build can't influence another, and protecting the provenance-signing key so user-defined build steps can never read it. The practical payoff is that a consumer can cryptographically verify "this artifact came from this pipeline at this commit," which is what stops dependency-substitution and tampering attacks. I pair it with dependency pinning, SBOM generation, and cosign signing of the output.

</details>

<details>
<summary><strong>Q:</strong> Push-based vs pull-based (GitOps) deployment — what changes about credentials, drift, and rollback?</summary>

Senior model answer: In push, the pipeline holds cluster credentials and applies changes outward — simple and direct, but CI now has standing prod write access and any manual `kubectl` drift is invisible. GitOps inverts it: Git holds desired state, and an in-cluster reconciler (Argo CD/Flux) continuously pulls and converges, so CI never holds cluster creds, drift is auto-corrected, the audit trail is the commit history, and rollback is `git revert`. The cost is another control plane to operate and the subtlety that reconciliation success ("manifests applied") isn't the same as application health — so I still gate on real health/SLO checks, not just sync status. For regulated/multi-cluster fleets the GitOps audit and least-privilege story usually wins.

</details>

<details>
<summary><strong>Q:</strong> How do you keep flaky tests from destroying pipeline signal without just turning off failing tests?</summary>

Senior model answer: Flaky tests are corrosive because they train engineers to "just re-run," which masks real regressions, so I treat flakiness as a first-class bug. I detect it by tracking pass/fail variance across runs, then *quarantine* the flaky test out of the gating path (it still runs and reports, but doesn't block) and file it for a real fix with an owner and deadline — not delete it. I never wrap the whole suite in blanket `retry`, because that converts a flaky failure into a hidden one; targeted retry is only acceptable around genuinely external, idempotent calls. Structurally, ordering the test pyramid so fast deterministic unit tests gate first reduces how often flaky slow tests are even on the critical path.

</details>

<details>
<summary><strong>Q:</strong> Design a CI/CD pipeline for a containerized microservice deployed to Kubernetes across multiple regions.</summary>

Senior model answer: PR pipeline runs the test pyramid in parallel on ephemeral container agents — fast unit gate first with `failFast`, then integration — plus static analysis and dependency scanning; nothing merges without green. On merge to main, build hermetically in a pinned container, produce a digest-addressed image, generate an SBOM, sign the image (cosign) and attach SLSA provenance from the build service. Promotion is environment-by-environment with the same artifact (build once, deploy many): dev→staging→prod, each gated. Prod uses GitOps — the pipeline bumps the image digest in a Git repo and Argo CD reconciles per region, doing a canary with automated SLO analysis that aborts and reverts on breach. Rollback is `git revert` of the digest plus feature-flag kill switches for behaviour. Region rollout is staggered (canary one region, bake, then fan out) so a regional issue never goes global at once.

</details>

<details>
<summary><strong>Q:</strong> Design the promotion flow across environments. How do you guarantee the thing you tested is the thing you ship?</summary>

Senior model answer: The core rule is **build once, promote the same immutable artifact** — never rebuild per environment, because a rebuild can pull different dependencies and invalidate your testing. The pipeline produces one digest-addressed image with attached provenance; staging and prod deploy *that exact digest*, and config differences are injected at deploy time (env vars, ConfigMaps, secrets), never baked in. Each environment is a gate with its own checks — staging runs integration/E2E and soak, prod requires an explicit or policy-based approval — and the promotion record ties artifact digest → commit → approver for audit. Fingerprinting/provenance verification at the gate confirms the digest being promoted is the one that passed the prior stage, so there's no "rebuilt and slightly different" gap.

</details>

<details>
<summary><strong>Q:</strong> On your Oracle work you migrated an API-gateway performance-testing stack to Java 21 and a new framework, and replaced ticket-driven dependencies with Terraform. Walk me through how that changed your pipeline's reliability and reproducibility.</summary>

Senior model answer: The legacy Canary-based suite was a reproducibility liability — provisioning depended on manual tickets that took ~30 days and produced snowflake environments, so a perf run was never cleanly repeatable. Migrating to the new Test Service on Java 21 with a modern framework let me pin the toolchain and run in controlled, current infra, and codifying the dependencies in Terraform collapsed provisioning from 30 days to about 8 hours while making every environment declarative and identical. That's the hermeticity story in practice: the infra became code, so a perf environment could be torn down and recreated deterministically instead of hand-built. Retiring the legacy instances also closed the standing-risk surface — it avoided 300+ security tickets across 34 regions, which is exactly the supply-chain/attack-surface reduction a senior owns end to end.

</details>

<details>
<summary><strong>Q:</strong> At UnitedHealth you automated a Pega install from 11 hours to 30 minutes and built cert-rotation and go-live validation automation. How do those map to CI/CD principles?</summary>

Senior model answer: The Pega install automation is the reproducibility-and-throughput principle: an 11-hour manual install is non-deterministic and error-prone, so scripting it to 30 minutes turned a fragile runbook into a repeatable, idempotent step — the same inputs reliably produce the same environment. Cert-rotation automation is secrets hygiene: rotating credentials on a schedule shrinks the window any leaked secret is useful, which directly addresses the secrets-management failure mode. Go-live validation automation is the post-deploy health gate — automated checks that confirm the release is actually healthy before declaring success, which is the prerequisite for safe, fast rollback. Together they're the same theme: replace slow manual steps with automated, gated, repeatable ones so deploys get smaller, more frequent, and safer.

</details>

## Say it with your resume

- **Led the API-gateway performance-testing stack modernization at Oracle** — migrated off legacy Canary to the new Test Service, upgraded to **Java 21** and a new testing framework, and built the supporting infra. This is my "make the pipeline hermetic and current" story: pinned toolchain, controlled environments, repeatable perf runs.
- **Replaced ticket-driven dependencies with Terraform automation, cutting provisioning from 30 days to 8 hours** — the infrastructure-as-code half of reproducibility: environments are declarative, identical, and tear-down/recreate-able instead of hand-built snowflakes.
- **Retired legacy instances and avoided 300+ security tickets across 34 regions** — attack-surface and supply-chain risk reduction owned end to end, the kind of standing-risk cleanup a senior drives.
- **At UnitedHealth, automated a Pega install from 11h to 30min** — turned a fragile manual runbook into a repeatable, idempotent pipeline step (throughput + reproducibility).
- **Built cert-rotation and go-live validation automation at UnitedHealth** — secrets hygiene (shrinking the leaked-credential window) and the automated post-deploy health gate that makes fast, safe rollback possible.

## Sources

- [Jenkins Documentation](https://www.jenkins.io/doc/)
- [Jenkins Pipeline Syntax (declarative/scripted, agents, parallel, when)](https://www.jenkins.io/doc/book/pipeline/syntax)
- [Using a Jenkinsfile — credentials and secret handling](https://www.jenkins.io/doc/book/pipeline/jenkinsfile)
- [Credentials Binding plugin steps (withCredentials, interpolation gotcha)](https://www.jenkins.io/doc/pipeline/steps/credentials-binding)
- [Jenkins Pipeline — tests and artifacts (archiveArtifacts, junit)](https://www.jenkins.io/doc/pipeline/tour/tests-and-artifacts)
- [SLSA Framework overview (Wiz)](https://www.wiz.io/academy/application-security/slsa-framework)
- [What is the SLSA Framework? (JFrog)](https://jfrog.com/learn/grc/slsa-framework/)
- [Deployment strategies: types, trade-offs, how to choose (CircleCI)](https://circleci.com/blog/deployment-strategies-types-trade-offs-and-how-to-choose/)
- [Blue/green vs canary deployments (Octopus Deploy)](https://octopus.com/devops/software-deployments/blue-green-vs-canary-deployments/)
