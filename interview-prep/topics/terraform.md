---
title: Terraform
bucket: tech
must: true
gap: false
rank: 2
sources: https://developer.hashicorp.com/terraform/docs
generated: true
---

## 80/20 — Core concepts

- **Declarative IaC** — describe desired infra in HCL; Terraform computes the API calls to reach it. **Providers** (e.g. `hashicorp/aws`) are plugins that translate config into real API calls.
- **Resources** are managed objects (`resource "aws_instance" "main" {}`); **data sources** read existing external info without managing it.
- **State** (`terraform.tfstate`) maps your config to real-world objects + their attributes. Terraform diffs desired config against state to decide changes — state is the source of truth for what Terraform manages.
- **Workflow** — `terraform plan` produces an execution plan (create/update/destroy) without changing anything (`-out tfplan` to save); `terraform apply` executes it.
- **Idempotency** — because it converges to desired state, re-running `apply` with no config change is a no-op; it only acts on drift.
- **Modules** package reusable resource groups (inputs/outputs). **Remote state** (S3, HCP) enables team sharing + locking; `terraform_remote_state` lets one config read another's outputs.

## Likely interview questions

**Q:** What is the state file and why does it matter?
**A:** It maps declared resources to real provisioned objects and caches their attributes. Terraform diffs config against state to plan; losing/corrupting it means Terraform no longer knows what it manages — risking duplicate or orphaned resources.

**Q:** Difference between plan and apply?
**A:** `plan` is a dry run showing exactly what will be created/changed/destroyed; `apply` carries it out. Saving a plan (`-out`) and applying that file guarantees apply does exactly what you reviewed.

**Q:** Why remote state instead of local?
**A:** A team shares one authoritative state, gets locking to prevent concurrent corrupting writes, and keeps sensitive state off laptops. It also enables cross-stack references via `terraform_remote_state`.

**Q:** What makes Terraform idempotent?
**A:** It models desired end state, not steps. Re-applying unchanged config is a no-op because actual state already matches; it only reconciles detected drift.

## Say it with your resume

- **Direct hit:** "I cut OCI API Gateway new-region build time from **30 days to 8 hours** by replacing ticket-driven dependencies with **Terraform-based automation**." Lead with this — it proves IaC at real scale, not toy demos.
- Connect it to *idempotency* and *plan/apply discipline*: explain how declarative provisioning + reviewable plans made 34-region rollouts repeatable and safe.

## Sources

- [Terraform Documentation](https://developer.hashicorp.com/terraform/docs)
