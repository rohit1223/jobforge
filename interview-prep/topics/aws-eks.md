---
title: AWS & EKS
bucket: tech
must: true
gap: false
rank: 1
sources: https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
generated: true
---

## 80/20 — Core concepts

- **Managed control plane** — AWS runs/scales the Kubernetes API server + etcd across multiple AZs and handles patching/upgrades. You own workloads and (optionally) nodes.
- **Compute options** — *managed node groups* (EC2 EKS provisions & lifecycles), *self-managed nodes*, and *Fargate profiles* (serverless pods, no nodes). Karpenter is common for fast autoscaling.
- **IRSA (IAM Roles for Service Accounts)** — maps a K8s ServiceAccount → IAM role via an OIDC provider, giving pods **least-privilege** AWS access without node-wide credentials. (Newer EKS Pod Identity is an alternative; Fargate still needs IRSA.)
- **VPC CNI networking** — pods get **real VPC IPs** from cluster subnets via ENIs, so they're first-class VPC citizens with native routing + security groups. Core add-ons: `vpc-cni`, `kube-proxy`, `coredns`.
- **Load balancing** — the AWS Load Balancer Controller provisions an **ALB** for `Ingress` (L7) and an **NLB** for `Service type=LoadBalancer` (L4); `target-type=ip` routes straight to pod IPs.

## Likely interview questions

**Q:** What does "managed control plane" mean in EKS?
**A:** AWS operates the K8s masters (API server + etcd) across multiple AZs — availability, scaling, patching, upgrades. You're responsible for worker capacity (node groups/Fargate) and your workloads.

**Q:** Managed node groups vs. Fargate?
**A:** Node groups are EC2 instances whose lifecycle EKS automates — you pick instance types and can run DaemonSets. Fargate runs pods serverlessly (no nodes to patch/scale, sized per pod) but with constraints (no DaemonSets, requires IRSA).

**Q:** What is IRSA and why use it?
**A:** It binds a ServiceAccount to an IAM role via the cluster's OIDC provider, so individual pods get scoped credentials instead of broad node instance-profile permissions — the secure way to let a pod reach S3/SQS/etc.

**Q:** How does pod networking work and how do you expose services?
**A:** The VPC CNI gives each pod a real VPC IP via ENIs, routable within the VPC. Expose them with the AWS Load Balancer Controller — ALB for Ingress (L7) or NLB for LoadBalancer Services (L4), `target-type=ip` to hit pod IPs directly.

## Say it with your resume

- **Direct hit:** "At UnitedHealth I containerized Pega and deployed it to **AWS EKS and ECS**, publishing images to **ECR** and wiring secure access with **IAM, ALB, Route 53, and VPC**." That single bullet touches control plane, registry, load balancing, identity, and networking — walk it as your EKS story.
- Tie IAM/ALB/VPC there to the concepts above (IRSA-style scoped access, L7 routing, pods-in-VPC) to show you understand the *why*, not just the service names.

## Sources

- [Amazon EKS User Guide](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
