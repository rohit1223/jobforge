---
title: Argo CD & GitOps
bucket: tech
must: false
gap: true
rank: 6
sources: https://argo-cd.readthedocs.io/en/stable/core_concepts/
generated: true
---

> **Gap focus** — Sensorfact uses **ArgoCD** for CD. You haven't run it, but your Terraform/declarative-automation mindset is the right foundation. Learn the vocabulary; bridge from IaC.

## 80/20 — Core concepts

- **Declarative GitOps** — Git is the single source of truth for desired cluster state; Argo CD continuously reconciles the cluster to match it. Deploy = commit to Git.
- **Application** is a CRD (`argoproj.io/v1alpha1, kind: Application`) defining a `source` (repo, path, targetRevision) and a `destination` (cluster + namespace).
- **Target vs. Live state** — target = what's in Git, live = what's running. **Sync status** (`Synced`/`OutOfSync`) = drift detection. **Health status** (Healthy/Progressing/Degraded) = runtime health — separate axis.
- **Sync** applies Git manifests to the cluster (manual or automated).
- **`syncPolicy.automated`** auto-applies Git changes; **`selfHeal: true`** reverts manual cluster drift back to Git; **`prune: true`** deletes resources removed from Git.
- **Sync waves** order resources into phases; **resource hooks** (`PreSync`/`Sync`/`PostSync`) run jobs like DB migrations at defined points.

## Likely interview questions

**Q:** What is GitOps and how does Argo CD implement it?
**A:** Git holds declarative desired state; Argo CD watches Git + cluster and reconciles them. You deploy by committing — giving auditability, rollback via revert, and one source of truth.

**Q:** Synced vs. Healthy?
**A:** Sync compares live config to Git (drift). Health is runtime status — a Deployment with crashing pods can be Synced but Degraded. Both must be good for a successful rollout.

**Q:** What do prune and selfHeal do?
**A:** `prune` deletes cluster resources no longer in Git. `selfHeal` automatically reverts out-of-band manual changes back to the Git-defined state, preventing drift.

**Q:** What are sync waves and hooks for?
**A:** Sync waves order resource application into phases (e.g. CRDs before workloads). Hooks (PreSync/Sync/PostSync) run tasks like migrations or smoke tests at defined points in the sync lifecycle.

## Say it with your resume

- **Honest bridge:** "I haven't run Argo CD in production, but I've lived the declarative model — replacing **ticket-driven dependencies with Terraform** is the same idea: desired state in code, reconcile to it. GitOps just moves that loop into Git + a controller, and the drift/self-heal concepts are familiar from infra reconciliation."
- Mention your enforcement habits (RBAC, tenant validation, guardrails) — GitOps shops care about who can change what, and you've built that thinking.

## Sources

- [Argo CD Core Concepts](https://argo-cd.readthedocs.io/en/stable/core_concepts/)
