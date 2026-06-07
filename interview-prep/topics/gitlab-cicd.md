---
title: GitLab CI/CD
bucket: tech
must: true
gap: true
rank: 4
sources: https://docs.gitlab.com/ci/
generated: true
---

> **Gap focus** — Sensorfact runs **GitLab CI**; your hands-on CI/CD is **Jenkins**. The concepts map almost 1:1 — be honest, then bridge from Jenkins.

## 80/20 — Core concepts

- Pipelines are defined in **`.gitlab-ci.yml`** at the repo root; triggered by pushes, MRs, tags, or schedules.
- **Stages** are ordered phases (`build → test → deploy`); **jobs** belong to a stage. Jobs in a stage run in parallel; the next stage starts only after the prior succeeds.
- **Jobs** have a `script` (commands), optionally an `image` (Docker image to run in), and run on **runners**. `allow_failure: true` lets a job fail without blocking.
- **Runners** are the agents executing jobs via executors — Docker (clean container per job), Shell (host), or Kubernetes (job-per-pod). Shared, group, or project-scoped.
- **Artifacts** pass build outputs downstream (`artifacts.paths`, `expire_in`); pulled via `dependencies`. **Cache** reuses dependencies across runs — different purpose from artifacts.
- **Environments** (`environment: name/url`) model deploy targets + track history; **rules** (`rules: - if: $CI_COMMIT_BRANCH == 'main'`) conditionally gate jobs.

## Likely interview questions

**Q:** How are stages and jobs related?
**A:** Stages run sequentially in declared order; all jobs in a stage run in parallel. A stage begins only once every job in the prior stage succeeds (unless `allow_failure`) — a build→test→deploy gate flow.

**Q:** What is a runner and what executors exist?
**A:** A runner picks up and executes jobs. Executors set the environment — Docker (clean container), Shell (host), or Kubernetes (job-per-pod). Runners can be shared or dedicated.

**Q:** How do you pass build output between jobs?
**A:** `artifacts.paths` uploads files from one job; downstream jobs download them (or scope via `dependencies`). Artifacts pass results; cache reuses dependencies across runs.

**Q:** How do you deploy only on main?
**A:** Use `rules` with `if: $CI_COMMIT_BRANCH == "main"` (or `$CI_COMMIT_TAG`), combined with `environment:` — e.g. staging on main, production on tags.

## Say it with your resume

- **Honest bridge:** "My CI/CD depth is in **Jenkins** — I modernized the API Gateway performance-testing stack end to end, migrating the suite to a new framework on Java 21 and building the supporting pipeline infra. The GitLab CI model (stages, runners, artifacts, rules) maps directly, and I'd be productive quickly."
- Don't claim GitLab CI experience you don't have. Show you grasp the *concepts* and have shipped real pipelines — that's what they're testing.

## Sources

- [GitLab CI/CD Documentation](https://docs.gitlab.com/ci/)
