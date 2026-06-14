---
title: GitLab CI
bucket: tech
learning: true
depth: deep
detailed: true
sources: https://docs.gitlab.com/ci/yaml/, https://docs.gitlab.com/ci/caching/, https://docs.gitlab.com/ci/pipelines/downstream_pipelines/, https://docs.gitlab.com/ci/variables/
added: 2026-06-13
generated: true
---

> **Learning topic.** Your CI/CD depth is Jenkins (plus Terraform-driven build automation); Sensorfact runs GitLab CI. The concepts transfer almost 1:1 — pipelines, agents/runners, artifacts, gated deploys — but GitLab's model is **declarative YAML in the repo** with a **pull-based runner fleet**, where Jenkins is a controller pushing work to agents with pipeline logic often living in Groovy. Frame answers as "here's the concept I've run in production on Jenkins, and here's how GitLab expresses it."

## Core concepts

### Prerequisites — the mental model before the keywords

- **Everything is `.gitlab-ci.yml` in the repo.** A pipeline is *derived* from the file at the commit being built — config is versioned with the code, branches can change their own pipeline, and there is no central job configuration to drift (a classic Jenkins pain). One file can `include:` others (local files, other projects, remote URLs, templates, CI/CD components), so platform teams publish reusable pipeline fragments instead of shared Groovy libraries.
- **Runners pull, the server never pushes.** A *runner* is an agent (binary or K8s deployment) that polls the GitLab server for queued jobs matching its **tags**, executes them in its **executor** (shell, `docker`, `kubernetes`, …), and streams logs back. The server holds no execution capacity. This inverts Jenkins' controller→agent push model: runners can live behind NAT, scale horizontally, and a dead runner just stops polling.
- **Every job is an isolated, ephemeral environment.** With the docker/kubernetes executors each job starts in a fresh container from `image:`. Nothing survives a job except what you explicitly declare as **artifacts** (passed forward) or **cache** (best-effort reuse). Jenkins habits of "the workspace is still there from last build" do not transfer — this is the #1 migration trip-wire.

### Pipeline anatomy (mechanism)

- **`stages` + `jobs`.** Jobs in the same stage run in parallel (runner capacity permitting); stages run in sequence. A job without `stage:` lands in `test`. `default:` sets job-level defaults (image, before_script, …); `variables:` at the top level seeds every job.
- **Reuse:** hidden jobs (`.lint-base:`) + `extends:` give inheritance; YAML anchors work too; `include:` composes files. `extends` merges shallowly — hashes merge, arrays REPLACE (a `script:` in the child wipes the parent's, a common surprise).
- **`rules:` decide whether a job exists in this pipeline** — evaluated at pipeline *creation*, first match wins: `if:` (expressions over CI variables), `changes:` (paths touched), `exists:`, with outcomes `when: on_success / manual / delayed / never` and per-rule `variables:`. `rules:` replaced `only/except`; never mix them in one job. **`workflow: rules:`** is the same idea at pipeline level — it decides whether the whole pipeline is created.
- **`needs:` builds a DAG across stages.** A job with `needs: [build_a]` starts the moment `build_a` finishes — it does not wait for its stage. `needs: []` starts immediately. By default a `needs` relationship also downloads that job's artifacts. This is how you cut a 30-min staged pipeline to the critical path; stages remain as a readability/grouping device.

### Pipeline types and the duplicate-pipeline gotcha

- Push to a branch → **branch pipeline** (`CI_PIPELINE_SOURCE == "push"`). Open MR → **merge request pipeline** (`"merge_request_event"`, runs on a prospective merge context). Without care, one push to a branch with an open MR creates **both**. The canonical fix (doc-blessed):

```yaml
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS
      when: never
    - if: $CI_COMMIT_BRANCH
```

- **Merged results pipelines** test the MR as if merged into the target; **merge trains** queue MRs and test each against the train ahead of it — the fix for "both MRs passed alone, broke together" at high merge volume.

### Runners, executors, and building images (mechanism + trade-offs)

- **Executor choice:** `shell` (fast, zero isolation — jobs share the host, only sane for trusted/dedicated boxes), `docker` (each job a container; the default choice), `kubernetes` (each job a pod; scales with the cluster, fits an EKS shop). **Tags route jobs to runners**; an untagged job waits for an untagged runner — "job stuck in pending" is almost always a tag/runner mismatch.
- **`services:`** spin up sidecar containers (Postgres, Redis, `docker:dind`) network-aliased to the job — that's how integration tests get a real database.
- **Building Docker images inside CI** is its own decision: *docker-in-docker* (`docker:dind` service) requires `privileged = true` on the runner — a real security trade-off on shared runners; *socket-binding* mounts the host's docker.sock (faster, but jobs can see/kill each other's containers); daemonless builders (kaniko/buildah) avoid privileged mode at some compatibility cost. Know the trade-off, not just one recipe.
- **Concurrency** is runner-side: `concurrent` in `config.toml` caps simultaneous jobs per runner process; autoscaling runners (docker-machine successor, k8s) add capacity. Job-side: `parallel: N` / `parallel: matrix:` fan a job out; `resource_group:` serializes (see deployments).

### Cache vs artifacts — different contracts (the classic trap)

| | `cache:` | `artifacts:` |
|---|---|---|
| Purpose | reuse dependencies between *runs* | pass job *outputs* downstream + to UI |
| Guarantee | **best-effort** — may be absent | guaranteed to later stages / `needs` |
| Lives | on the runner (or distributed S3/GCS store) | on the GitLab server |
| Scope | keyed by `cache:key` | per-pipeline, `expire_in`, `dependencies:` |

- Cache keyed well: `key: files: [package-lock.json]` → re-keyed only when the lockfile changes; `policy: pull` for consumers so ten test jobs don't all re-upload. **Gotcha:** with multiple/autoscaled runners and *no distributed cache*, each runner has its own local cache — jobs hit different machines and "the cache randomly disappears". Configure the S3/GCS distributed cache or pin cache-heavy jobs to tagged runners.
- `artifacts: reports:` (junit, coverage, etc.) feed MR widgets — test failures appear inline in the MR, which is much of GitLab's review UX.

### Variables, secrets, and OIDC

- **Precedence (high→low, roughly):** trigger/schedule/pipeline-run variables → project UI → group UI → instance → `.gitlab-ci.yml` → job defaults. A UI variable silently overriding a YAML one is a classic debugging hour.
- **Protected variables** are only injected into pipelines on protected branches/tags — that, plus protected environments, is the guardrail that keeps a feature-branch pipeline from holding prod credentials. **Masked** hides values in logs (best-effort — base64 or split secrets still leak).
- **`id_tokens:`** mint short-lived OIDC JWTs per job; cloud providers (AWS IAM OIDC, Vault) trust them → **no long-lived cloud keys in CI variables at all**. This is the modern answer to "how do you give CI AWS access" and pairs directly with EKS/IRSA thinking.

### Downstream pipelines, environments, deployments

- **Parent-child:** `trigger: include: child.yml` runs a child pipeline in the same project — and the child YAML can be **generated by an earlier job** (dynamic pipelines: monorepos emit one child per changed component via `rules:changes`). **Multi-project:** `trigger: project: group/other-repo` chains repos; `strategy: depend/mirror` ties the parent's result to the child's.
- **`environment:`** on a deploy job records deployments against a named environment with a URL; `name: review/$CI_COMMIT_REF_NAME` per MR = **review apps**, torn down by an `on_stop` job when the MR closes. Protected environments gate who/what can deploy.
- **`resource_group: production`** serializes deploy jobs across the whole project — two pipelines can't deploy prod concurrently. **Deadlock gotcha (doc-flagged):** put the `resource_group` on the *trigger job in the parent*, not only inside a child pipeline, or the parent can hold the lock the child is waiting for.

### Failure modes & tuning knobs that matter

- *Stuck pending* → tag/runner mismatch or saturated `concurrent`. *Works locally, fails in CI* → fresh-container assumption broken (missing artifact/cache declaration). *Random cache misses* → no distributed cache behind autoscaled runners. *Duplicate pipelines* → missing `workflow:rules`. *Secret in logs* → unmasked variable or `set -x`.
- Levers for speed at scale: `needs:` (DAG over stages), `interruptible: true` + auto-cancel redundant pipelines (kill superseded runs on force-push), `rules:changes` to skip untouched components, `parallel: matrix:` for test sharding, well-keyed pull-policy caches, child pipelines to keep YAML evaluable and focused. `timeout:` per job and `retry: max: 2, when: runner_system_failure` to absorb infra flakes without masking real failures.

### Worked example — the shape of a production pipeline

```yaml
workflow:                       # MR pipelines, no duplicates
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS
      when: never
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

default:
  image: node:22-alpine
  interruptible: true

stages: [build, test, package, deploy]

install:
  stage: build
  cache:
    key: { files: [package-lock.json] }
    paths: [node_modules/]
  script: [npm ci]
  artifacts: { paths: [node_modules/], expire_in: 1h }

unit-tests:
  stage: test
  needs: [install]
  parallel: 4
  script: [npx jest --shard=$CI_NODE_INDEX/$CI_NODE_TOTAL --reporters=jest-junit]
  artifacts:
    reports: { junit: junit.xml }

package-image:
  stage: package
  needs: [unit-tests]
  image: gcr.io/kaniko-project/executor:debug    # no privileged dind
  script:
    - /kaniko/executor --context $CI_PROJECT_DIR
      --destination $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

deploy-prod:
  stage: deploy
  needs: [package-image]
  id_tokens: { AWS_TOKEN: { aud: https://gitlab.example.com } }  # OIDC → IAM, no static keys
  script: [./deploy.sh $CI_COMMIT_SHORT_SHA]
  environment: { name: production, url: https://app.example.com }
  resource_group: production
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      when: manual
```

## Interview questions

<details>
<summary><strong>Q:</strong> Walk me through what happens between `git push` and a job's first log line in GitLab CI.</summary>

GitLab evaluates `workflow:rules` to decide whether to create a pipeline, then evaluates each job's `rules:` against the push context to materialize the job graph (stages + `needs` DAG) — all from `.gitlab-ci.yml` *at that commit*. Jobs become `pending` in a queue; runners poll the server for jobs matching their tags, claim one, and the executor provisions the environment (e.g., pulls `image:` and starts a fresh container, plus any `services:`). The runner injects variables, restores cache, downloads artifacts from `needs`/earlier stages, runs `before_script`+`script`, and streams logs back. Key contrast with Jenkins: the server never pushes work — capacity is entirely runner-side.

</details>

<details>
<summary><strong>Q:</strong> A job sits in "pending" forever. Diagnose it.</summary>

It's almost always job→runner matching: the job's `tags:` don't match any online runner, the matching runners are paused/offline, or untagged jobs aren't allowed by the only available (tagged) runners. Second cause: capacity — runners' `concurrent` limit saturated, so jobs queue. Check the job's tags vs the project's available runners, runner status, and queue depth; on Kubernetes also check the runner manager can actually schedule pods (quota, node capacity). If it's protected-branch related, a protected variable/environment can also keep specific runners from picking up the job.

</details>

<details>
<summary><strong>Q:</strong> Explain cache vs artifacts. When does using one as the other bite you?</summary>

Artifacts are the contract: job outputs uploaded to the server, guaranteed available to later stages/`needs` jobs, surfaced in the UI and `reports:`. Cache is an optimization: best-effort, stored runner-side (or in a distributed S3/GCS store), keyed by `cache:key`, and may simply be absent. Using cache to pass build outputs forward breaks the moment the next job lands on a different autoscaled runner without distributed cache — "works sometimes" pipelines. Using artifacts as a dependency cache hammers the server with huge uploads on every job and slows everything. Rule: outputs → artifacts, dependencies → cache keyed on the lockfile (`key: files:`), consumers with `policy: pull`.

</details>

<details>
<summary><strong>Q:</strong> What's the difference between `rules` and `workflow:rules`, and how do rules interact with pipeline creation?</summary>

`workflow:rules` runs once at pipeline level and decides whether the pipeline exists at all; job `rules:` decide whether each job is included in that pipeline. Both are evaluated at pipeline *creation* time, first match wins, and a job with no matching rule (or `when: never`) simply isn't created. Because evaluation happens at creation, rules can't react to runtime results — that's what `needs` + job status, `allow_failure`, or dynamic child pipelines are for. Per-rule `variables:` let one job behave differently per trigger context.

</details>

<details>
<summary><strong>Q:</strong> Your team pushes to a branch with an open MR and gets two pipelines per push. Why, and what's the fix?</summary>

Push events create branch pipelines and the open MR creates a merge request pipeline — they're distinct pipeline types with different contexts (`CI_PIPELINE_SOURCE` of `push` vs `merge_request_event`), so you pay double CI. The doc-canonical `workflow:rules` switcher runs MR pipelines when one exists and suppresses the branch pipeline while an MR is open (`if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS → when: never`), still allowing branch pipelines otherwise — plus default-branch pipelines for post-merge.

</details>

<details>
<summary><strong>Q:</strong> How does `needs` change pipeline execution, and what limits it?</summary>

`needs` overlays a DAG on the stage model: a job starts when its needed jobs finish, ignoring stage barriers, and by default fetches artifacts only from those jobs — wall-clock collapses to the critical path. `needs: []` starts a job immediately. Limits: the needed job must exist in the pipeline (rules interactions cause "job uses needs but it doesn't exist" failures), there's a max needs count per job, and overusing it turns YAML into a hand-maintained graph — keep stages for narrative, `needs` for the hot path.

</details>

<details>
<summary><strong>Q:</strong> Compare the shell, docker, and kubernetes executors and when you'd pick each.</summary>

Shell runs jobs directly on the runner host: fastest, zero isolation — only acceptable on dedicated, trusted runners (and it's how you get state bleeding between jobs). Docker gives each job a fresh container from `image:` with `services:` sidecars — the default for isolation + reproducibility on VM fleets. Kubernetes schedules each job as a pod: elasticity from the cluster, native fit when your platform is already EKS, at the cost of pod-startup latency and more moving parts (RBAC, quotas, volumes for dind). The decision is isolation/elasticity vs startup overhead and operational complexity.

</details>

<details>
<summary><strong>Q:</strong> You need to build and push Docker images from CI. What are your options and their security trade-offs?</summary>

Three options. Docker-in-docker (`docker:dind` service): full daemon per job, but the runner must run `privileged = true` — root-equivalent on the host, unacceptable on shared runners. Socket binding (mount host docker.sock): fast, layer cache shared, but every job can control the host daemon — see, stop, or exec into other jobs' containers. Daemonless builders (kaniko, buildah): build in userspace without privileged mode — the right default on shared/k8s runners, with occasional Dockerfile-compat caveats. At a previous role I'd also isolate image-build jobs to a dedicated tagged runner pool to contain blast radius.

</details>

<details>
<summary><strong>Q:</strong> Pipelines on your autoscaled runner fleet show "random" cache misses. Walk through your diagnosis.</summary>

Cache is per-runner local storage unless a distributed cache is configured. With autoscaling, consecutive jobs land on different machines, so hit rate is luck. Confirm by correlating cache hits with runner hostname in job logs. Fixes: configure the distributed cache (S3/GCS) in `config.toml` so all runners share one store; or pin cache-heavy jobs to a small tagged pool; and check the key strategy — `key: files: [lockfile]` so unrelated branches share dependency caches instead of fragmenting per-branch. Also verify consumers use `policy: pull` so they don't race to re-upload.

</details>

<details>
<summary><strong>Q:</strong> How do variables get into a job, and why might a value differ from what's in `.gitlab-ci.yml`?</summary>

Variables merge from many scopes with precedence: pipeline-run/trigger/schedule variables beat project UI settings, which beat group, instance, then YAML (`variables:` global, then job-level). So a UI-defined variable silently overrides the YAML default — the classic "but the file says X" bug. Additional wrinkles: protected variables only exist on protected refs (a job behaves differently on a feature branch), rules-level `variables:` rewrite values per trigger context, and masked variables alter what you can see in logs, not the value. Debug with a controlled `env | sort` job and check each scope.

</details>

<details>
<summary><strong>Q:</strong> How would you give pipelines AWS access without storing cloud keys in CI variables?</summary>

Use `id_tokens:` — each job mints a short-lived OIDC JWT signed by GitLab with claims (project, ref, environment). Configure AWS IAM as an OIDC federation trust on those claims and the job exchanges its token for temporary STS credentials scoped by role policy — no long-lived secrets to rotate or leak, and trust conditions like "only `main`, only environment `production`" are enforced by IAM, not by who can read a variable. Same pattern works for Vault. Static keys in protected+masked variables are the fallback, strictly worse.

</details>

<details>
<summary><strong>Q:</strong> What problem do `resource_group`s solve, and what's the known deadlock pattern with child pipelines?</summary>

`resource_group: production` makes deploy jobs across all pipelines mutually exclusive — two merged MRs can't run `deploy-prod` concurrently and interleave a rollout; jobs queue per resource (process mode can enforce ordering). The deadlock: if a parent's trigger job spawns a child pipeline and the *child* job wants the same resource group while the *parent* trigger also holds one (or strategy waits on the child), they can wait on each other. Doc guidance: attach the `resource_group` to the trigger job in the parent (with `strategy: mirror/depend`) so the lock is acquired once at the right level.

</details>

<details>
<summary><strong>Q:</strong> Design CI for a monorepo with ~10 services so a one-service change doesn't run everything.</summary>

Two composable mechanisms. First, `rules: changes:` on per-service jobs (or per-service `include`d files) so jobs only materialize when their paths change — works, but the YAML grows linearly and globally. Second, dynamic parent-child pipelines: a cheap generator job inspects the diff, emits a child YAML per affected service, and a `trigger: include:` job runs each child — pipelines stay small, services own their child config, and `strategy: depend` propagates failure. Add `needs` inside each child for critical path, shared caches keyed per service, and an `interruptible` default so superseded pushes auto-cancel. Mention the limit: `changes:` evaluates against the right base only in MR pipelines — on branch pipelines pick the comparison ref deliberately.

</details>

<details>
<summary><strong>Q:</strong> What are merged results pipelines and merge trains, and when do you actually need trains?</summary>

An MR pipeline can run against the MR's source branch as-is; a *merged results* pipeline tests the prospective merge commit (source merged into target) — catching "green alone, red after merge" against the current target. Merge trains extend that under high merge volume: queued MRs each build against the train ahead of them (target + all earlier queued MRs), so the order that will actually land is what gets tested; a failure drops that MR out and rebuilds the ones behind. You need trains when merge frequency is high enough that the target moves between an MR's last pipeline and its merge — the same race semaphore/main-protection rules can't solve.

</details>

<details>
<summary><strong>Q:</strong> A deploy job must run only for the default branch, only manually, and never concurrently. Express that and explain each piece.</summary>

```yaml
deploy-prod:
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
      when: manual
  resource_group: production
  environment: { name: production, url: https://app.example.com }
```

`rules` gates job creation to default-branch pipelines and makes it a manual gate (note: a manual rule defaults `allow_failure: true` so the pipeline doesn't block — set it false if later stages must wait). `resource_group` serializes executions project-wide. `environment` records the deployment, enables protected-environment approval rules, and powers rollback from the environments UI.

</details>

<details>
<summary><strong>Q:</strong> How do `extends`, `include`, and YAML anchors differ for reuse, and where does each break down?</summary>

Anchors are plain YAML within one file. `extends` merges a (usually hidden `.base`) job into another across included files — but it's a shallow-ish merge: hashes merge key-by-key while arrays *replace*, so a child `script:` or `rules:` wipes the parent's, which surprises people building "base + extra step" patterns (use `!reference` to splice arrays). `include` composes whole files — local, other projects, remote URLs, templates, or versioned CI/CD components — which is how a platform team ships golden pipelines; the cost is action-at-a-distance: the effective config is assembled from many sources, so you debug with the merged-YAML view, not the file.

</details>

<details>
<summary><strong>Q:</strong> Your integration tests need Postgres and Redis. How does GitLab CI provide them and what are the classic failure modes?</summary>

`services:` starts sidecar containers alongside the job container, reachable by hostname alias (e.g., `postgres`, or a custom `alias:`); configure them via variables like `POSTGRES_PASSWORD`. Failure modes: the job starts before the service is *ready* (the runner waits for the port at best — apps must retry or use a health-wait script); on the kubernetes executor services share the pod's localhost network, so hostname assumptions from the docker executor break; and resource-starved runners OOM the sidecar first, which shows up as flaky connection-refused tests rather than an obvious kill.

</details>

<details>
<summary><strong>Q:</strong> What's your strategy for flaky-but-expensive pipelines — where do `retry`, `interruptible`, and `timeout` each fit?</summary>

`retry:` with `when:` filters (e.g., `runner_system_failure`, `stuck_or_timeout_failure`) absorbs *infrastructure* flakes without masking real test failures — blanket `retry: 2` on everything hides product bugs and doubles cost. `interruptible: true` plus auto-cancel redundant pipelines kills superseded runs on new pushes — the single biggest waste cut on busy MRs. `timeout:` per job (bounded by the runner's own max) turns hangs into fast failures. Beyond keywords: shard with `parallel:`, quarantine flaky tests via junit-report trends, and treat repeated `retry` triggers as an SLO signal on the runner fleet, not noise.

</details>

<details>
<summary><strong>Q:</strong> Review apps: how do `environment:`, dynamic names, and `on_stop` fit together?</summary>

A deploy job with `environment: name: review/$CI_COMMIT_REF_NAME, url: https://$CI_ENVIRONMENT_SLUG.example.com` creates one environment per MR branch, linked from the MR so reviewers click into a live instance. The environment declares `on_stop: stop_review`, pointing at a teardown job (`when: manual`, `environment: action: stop`) that GitLab runs when the MR merges/closes or the branch deletes — that auto-teardown is what keeps per-MR infrastructure from leaking. Auto-stop schedules (`auto_stop_in`) bound the lifetime even if events are missed.

</details>

<details>
<summary><strong>Q:</strong> You're migrating a large Jenkins estate to GitLab CI. What translates directly, and what needs redesign?</summary>

Direct translations: stages/jobs ↔ pipeline structure, agents+labels ↔ runners+tags, archived artifacts ↔ `artifacts:`, credentials ↔ protected/masked variables (better: OIDC), shared libraries ↔ `include`/components, input steps ↔ `when: manual` + protected environments. Needs redesign: anything assuming a persistent workspace (GitLab jobs are ephemeral — make state explicit as artifacts/cache); imperative Groovy logic (rules are declarative and creation-time — runtime branching becomes dynamic child pipelines or separate jobs); controller-centric plugins (replaced by runner features or first-class keywords); and Jenkins' single-controller scaling model (replaced by fleet design: tag taxonomy, autoscaling, distributed cache). I'd migrate one product line as a tracer, publish golden includes, and dual-run pipelines until parity is proven by artifact diffing.

</details>

<details>
<summary><strong>Q:</strong> A secret appeared in a job log. Walk through containment and prevention.</summary>

Contain: rotate the credential immediately (assume compromised), delete/redact the job log, and audit where else the same variable is readable (project/group inheritance, forks running MR pipelines). Root-cause: masking only filters exact matches — `set -x` tracing, base64, string-splitting, or printing a derived value bypasses it. Prevent: switch to `id_tokens` OIDC so there's nothing long-lived to leak; mark variables protected (not available to fork/feature pipelines) and masked; never enable debug tracing where secrets load; and gate who can edit CI config on protected branches since `.gitlab-ci.yml` itself can exfiltrate variables — that's why protected variables + protected branches must travel together.

</details>

<details>
<summary><strong>Q:</strong> Design the CI/CD platform for ~30 engineers shipping containerized services to EKS with GitLab CI. Cover runner architecture, image building, caching, and deploy safety.</summary>

Runners: kubernetes-executor runner managers in EKS on a dedicated node group (taints so CI can't starve prod), tag taxonomy (`k8s`, `dind-isolated`, `arm64`), autoscaling via cluster autoscaler/Karpenter, `concurrent` sized to node capacity. Image builds: kaniko (no privileged pods) pushing to ECR with OIDC-assumed roles — zero static keys. Caching: S3 distributed cache for dependency caches keyed on lockfiles; ECR layer cache for images. Pipelines: golden `include` components owned by platform; MR pipelines with merged results; `needs`-based DAG; junit reports for MR visibility. Deploy safety: per-environment protected environments + protected variables, `resource_group` per service-environment to serialize, review apps for MRs with `on_stop` teardown, manual gate (or merge train) into prod, and `environment:` tracking for one-click rollback. Observability: runner-fleet metrics (queue time as the SLO), cost per pipeline, auto-cancel + interruptible everywhere.

</details>

<details>
<summary><strong>Q:</strong> When would you choose multi-project pipelines over a parent-child split, and how does `strategy: depend` change behavior?</summary>

Parent-child stays within one project: shared variable context, one MR, ideal for monorepo decomposition and dynamically generated config. Multi-project (`trigger: project: group/app`) crosses repo boundaries — the downstream runs with *its own* config, permissions, and variables (only what you pass explicitly), fitting org seams: an app repo triggering a separately-owned deployment repo, or fan-out to dependent libraries. By default a trigger job succeeds once the downstream is *created*; `strategy: depend` (or `mirror`) makes the trigger job's result track the downstream pipeline's result, so the upstream MR actually gates on it — essential when the downstream is a required check rather than fire-and-forget.

</details>

## Say it with your resume

- **"I've built and owned CI/CD in production — the concepts are portable."** Your stack lists Jenkins, Docker, Kubernetes, Ansible/Chef; speak about pipeline design (stages, artifacts, gated deploys) from that base, then map keywords to GitLab equivalents explicitly.
- **Workflow automation at scale:** you cut OCI API Gateway new-region build time **30 days → 8 hours** by replacing ticket-driven dependencies with Terraform-based automation — exactly the "replace human handoffs with pipeline stages" story a CI platform interview wants; frame it as designing the dependency DAG, which is what `needs:` formalizes.
- **Pipeline as a product:** the AI-assisted weekly ops reporting pipeline (saving ~**240 dev-hours/month across 15 teams**) shows you build automated multi-stage pipelines with scheduled triggers, artifacts, and standardized outputs — GitLab scheduled pipelines + artifacts in different clothes.
- **Test-infrastructure migration:** migrating the performance-testing stack from legacy Canary to Test Service across **34 regions** (retiring legacy instances, resolving security findings) is your evidence for the "migrate Jenkins → GitLab without breaking teams" question: tracer migration, dual-run, parity proof, then retire.
- **Containerization:** customized JBoss/Tomcat images for OpenShift and the Docker Swarm/Ansible three-tier deployment back up the image-building discussion (dind vs kaniko, registries, repeatable provisioning).

## Sources

- [CI/CD YAML syntax reference](https://docs.gitlab.com/ci/yaml/)
- [Pipeline architecture (`needs`, DAG)](https://docs.gitlab.com/ci/pipelines/pipeline_architectures/)
- [Caching in GitLab CI/CD](https://docs.gitlab.com/ci/caching/)
- [Workflow rules / switch between pipeline types](https://docs.gitlab.com/ci/yaml/workflow/)
- [Downstream (parent-child & multi-project) pipelines](https://docs.gitlab.com/ci/pipelines/downstream_pipelines/)
- [Resource groups (and the child-pipeline deadlock)](https://docs.gitlab.com/ci/resource_groups/)
- [CI/CD variables & protection](https://docs.gitlab.com/ci/variables/)
- [Using Docker to build images (dind vs socket)](https://docs.gitlab.com/ci/docker/using_docker_build/)
- [Review apps](https://docs.gitlab.com/ci/review_apps/)
