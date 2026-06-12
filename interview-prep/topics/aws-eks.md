---
title: AWS & EKS
bucket: tech
must: true
rank: 1
sources: https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html
depth: standard
added: 2026-06-08
generated: true
---

## Core concepts

### Managed control plane: what AWS owns vs. what you own
EKS runs the Kubernetes control plane (API server, scheduler, controller-manager, and etcd) as a single-tenant, AWS-managed deployment spread across **at least two Availability Zones**, fronted by an NLB with health-checked API server instances. AWS owns control-plane HA, patching, etcd backups, and CVE backports; **you own everything from the kubelet down** — node OS/AMI patching, add-on versions, IAM, networking, and workloads. The boundary is a frequent source of confusion in incidents: a "control plane" outage is almost always actually your add-ons (CoreDNS, VPC CNI, kube-proxy) or node-level problems, not the AWS-managed components. The control plane reaches into your VPC through cross-account ENIs (the "cluster security group"), which is why webhook-based controllers (admission webhooks, the AWS Load Balancer Controller) require the control plane to reach pod/node ports — a classic cause of stuck `kubectl apply` when security groups block 9443.

### Compute models: managed node groups vs. self-managed vs. Fargate vs. Karpenter
- **Managed node groups (MNG):** AWS provisions an ASG of EKS-optimized AMIs, handles cordon/drain on rolling updates, and respects PodDisruptionBudgets. You still choose instance types and own AMI version bumps — **nodes are never auto-upgraded with the control plane**.
- **Self-managed:** raw ASG + your own launch template/AMI. Use when you need custom kernels, GPU drivers, or bootstrap logic MNG won't allow. You own drain/upgrade orchestration entirely.
- **Fargate:** one micro-VM per pod, no node management, strong isolation. Trade-offs: no DaemonSets, no privileged pods, no GPU, slower cold starts, and the VPC CNI is replaced (each pod gets a dedicated ENI). Pod Identity is **not** supported on Fargate — you must use IRSA there.
- **Karpenter:** the modern autoscaler. Unlike Cluster Autoscaler (which scales fixed-shape ASGs), Karpenter watches *unschedulable pods* and provisions **right-sized, just-in-time** EC2 directly from a flexible `NodePool`/`EC2NodeClass`, then **consolidates** (bin-packs and replaces underutilized nodes). Big wins: faster scale-up, Spot diversification, lower cost. Big gotcha: consolidation churns nodes — protect stateful/critical workloads with `disruption.budgets`, `do-not-disrupt` annotations, and PDBs, or you'll see surprise pod evictions.

### Pod-to-AWS identity: IRSA vs. EKS Pod Identity
Both bind an IAM role to a Kubernetes ServiceAccount for **least-privilege, per-workload** AWS credentials (no node-role sharing).
- **IRSA:** the cluster has an **OIDC provider**; pods get a projected service-account JWT, and the AWS SDK calls `AssumeRoleWithWebIdentity`. The role's trust policy hard-codes the cluster's OIDC issuer URL + `sub` (namespace/SA). Pain points: one OIDC provider and trust-policy edit **per cluster**, so a role isn't portable across clusters, and STS load scales per-pod.
- **EKS Pod Identity (newer):** no OIDC. A `pods.eks.amazonaws.com` trust principal makes one role reusable across **any** cluster; the **Pod Identity Agent** DaemonSet brokers credentials per node (so STS load is per-node, not per-pod) and supports **session tags** for ABAC. Cleaner separation of duties (IAM team vs. cluster team). Limits: Linux/EC2 only — **not Fargate, not Windows**; associations are eventually consistent (don't create them in hot paths). Default to Pod Identity for new clusters; keep IRSA for Fargate.

### VPC CNI: pods get real VPC IPs — and IP exhaustion is a real outage
The AWS VPC CNI assigns each pod a **routable VPC IP** from secondary IPs on the node's ENIs. This gives native security-group/flow-log visibility but couples pod density to ENI/IP limits. Max pods per node ≈ **(ENIs × (IPs-per-ENI − 1)) + 2**; e.g. an m5.large (3 ENIs × 10 IPs) tops out near ~29 pods regardless of free CPU/memory. **Failure mode:** in a busy /24-per-AZ subnet, the VPC simply runs out of IPs — new pods sit `ContainerCreating` with `failed to assign an IP address to container`, and node scale-up doesn't help. Mitigations: **prefix delegation** (`ENABLE_PREFIX_DELEGATION=true`) assigns /28 prefixes so each ENI yields 16× more IPs (raising the cap toward the 110-pod default), larger or dedicated pod subnets / **custom networking** (separate ENI subnet via `ENIConfig`), and tuning `WARM_IP_TARGET`/`MINIMUM_IP_TARGET` to trade EC2 API churn against pre-warmed IPs. Don't mix prefix and secondary-IP nodes in one group — roll new node groups instead.

### AWS Load Balancer Controller: ALB (L7) vs. NLB (L4), and target-type=ip
The controller reconciles an **ALB for `Ingress`** (L7: path/host routing, WAF, TLS termination, OIDC auth) and an **NLB for `Service type=LoadBalancer`** (L4: ultra-low latency, static IPs, preserves source IP). The key knob is **`target-type`**: `ip` registers **pod IPs directly** as targets (works because VPC CNI gives pods real IPs) — traffic bypasses the kube-proxy/NodePort hop, giving cleaner health checks, accurate load distribution, and graceful pod-readiness handling via the readiness-gate webhook. `instance` mode targets NodePorts (extra hop, SNAT can hide client IP). Prefer `ip` mode on EKS. Gotcha: pod-readiness gates + deregistration delay must be tuned or rolling deploys drop connections.

### Upgrades & version skew
A minor version gets **14 months standard support**, then **12 months extended support** (paid, +$ per cluster-hour) before AWS force-upgrades the control plane. Upgrade ordering: **control plane first, then add-ons (CoreDNS/kube-proxy/VPC CNI), then nodes** — and only **one minor version at a time**. Nodes/kubelet may lag the control plane by up to **3 minor versions** (kube tested), but never run ahead, and don't sit 3 behind in production. **Nodes are not auto-upgraded** with the control plane (MNG, self-managed, and Fargate all require an explicit node refresh). Pre-upgrade, scan for **removed APIs** (e.g. deprecated beta APIs) with a tool like `kubent`/`pluto`, since the API server will reject them after the bump.

### Cost & scaling gotchas
EKS bills **$0.10/hr per cluster** plus all EC2/Fargate/EBS/data. Cross-AZ traffic is **not free** — chatty service meshes or `externalTrafficPolicy: Cluster` can rack up inter-AZ charges; use `topology-aware routing`/`internalTrafficPolicy: Local` to keep traffic in-AZ. NAT Gateway data-processing costs surprise teams running image pulls through a single NAT; use VPC endpoints (ECR, S3) and per-AZ NATs. Karpenter consolidation saves cost but can violate latency SLAs via churn — budget it.

## Interview questions

<details>
<summary><strong>Q:</strong> When you say EKS is "managed," precisely what does AWS run and what stays your responsibility — and how does that boundary mislead people during incidents?</summary>

AWS runs the control plane (API server, scheduler, controller-manager, etcd) single-tenant across at least two AZs behind a health-checked NLB, plus etcd backups and CVE backports. You own everything from the kubelet down: node AMIs/patching, the core add-ons (CoreDNS, kube-proxy, VPC CNI), IAM, networking, and workloads — and crucially, **nodes are never auto-upgraded with the control plane**. The misleading part in incidents is that "control plane problems" are almost always your add-ons or nodes, not the AWS-managed bits; e.g. DNS failures are CoreDNS, and `kubectl apply` hanging on a CRD is usually an admission/LBC webhook the control plane can't reach because a security group blocks port 9443.

</details>

<details>
<summary><strong>Q:</strong> Compare IRSA and EKS Pod Identity. Why would a large org with many clusters prefer Pod Identity, and where can't you use it?</summary>

IRSA uses a per-cluster OIDC provider: pods present a projected SA token and call `AssumeRoleWithWebIdentity`, with the role's trust policy hard-coding that cluster's OIDC issuer and `sub`. That means a role isn't reusable across clusters (every cluster needs its own provider + trust edit) and STS load scales per-pod. Pod Identity drops OIDC entirely: a single `pods.eks.amazonaws.com` trust principal makes **one role reusable across all clusters**, the Pod Identity Agent brokers credentials per-node (less STS load), it supports session tags for ABAC, and it cleanly separates the IAM team's work from the cluster team's. A big multi-cluster org prefers it for reusability + separation of duties. But it's **Linux/EC2 only** — not Fargate, not Windows — so on Fargate you still use IRSA, and associations are eventually consistent so don't create them in startup hot paths.

</details>

<details>
<summary><strong>Q:</strong> Pods are stuck in ContainerCreating with "failed to assign an IP address to container," node CPU/memory is fine, and scaling out doesn't help. Walk the diagnosis.</summary>

This is VPC CNI IP exhaustion, not a compute problem. The VPC CNI hands each pod a real VPC IP from secondary IPs on the node's ENIs, so density is capped at roughly `(ENIs × (IPs-per-ENI − 1)) + 2`, and separately the **subnet itself can run dry**. I'd check the node's allocatable max-pods vs. running pods, then `aws ec2 describe-subnets` for available IPs in the AZ's pod subnet, and the `aws-node` (CNI) logs/`L-IPAMD` metrics. Fixes: enable **prefix delegation** (`ENABLE_PREFIX_DELEGATION=true`) so each ENI carries /28 prefixes (16× IPs), move pods to larger dedicated subnets via **custom networking/ENIConfig**, and tune `WARM_IP_TARGET`/`MINIMUM_IP_TARGET`. Roll *new* node groups for prefix mode rather than mixing prefix and secondary-IP nodes, which corrupts advertised capacity.

</details>

<details>
<summary><strong>Q:</strong> Explain `target-type: ip` vs `instance` in the AWS Load Balancer Controller. Why is `ip` usually the right default on EKS, and what breaks if you ignore readiness gates?</summary>

`instance` mode registers node NodePorts as targets, so traffic takes an extra kube-proxy hop, health checks are node-level (not pod-level), and SNAT can mask the client IP. `ip` mode registers **pod IPs directly** as load-balancer targets — possible because the VPC CNI gives pods routable IPs — eliminating the NodePort hop, giving accurate per-pod health and load distribution. It's the right default on EKS. The catch: during rolling deploys the LB must stop sending traffic to terminating pods and only send to ready ones. If you don't enable **pod readiness gates** (the LBC's webhook) and tune deregistration delay, the ALB/NLB keeps targeting pods that K8s already considers ready/terminating, and you drop in-flight connections on every deploy.

</details>

<details>
<summary><strong>Q:</strong> How would you choose between Karpenter and Cluster Autoscaler, and what's the production risk Karpenter introduces?</summary>

Cluster Autoscaler scales pre-defined, fixed-shape ASGs up/down to satisfy pending pods — predictable but you must curate instance families and it bin-packs poorly across shapes. Karpenter watches unschedulable pods and provisions **right-sized, just-in-time** instances from a flexible NodePool, diversifies across Spot pools, and **consolidates** by replacing underutilized nodes — typically faster scale-up and meaningfully lower cost. The risk is that consolidation actively churns nodes, so you can get surprise evictions on stateful or latency-sensitive workloads. You contain it with `disruption.budgets` (cap % nodes disrupted), `karpenter.sh/do-not-disrupt` annotations, `consolidationPolicy`/`consolidateAfter` timing, and real PodDisruptionBudgets.

</details>

<details>
<summary><strong>Q:</strong> Take me through a safe EKS minor-version upgrade in production. What's the ordering, the version-skew rules, and the failure you'd pre-empt?</summary>

Upgrade **one minor version at a time**, and never skip. Order: control plane first, then the managed add-ons (kube-proxy, CoreDNS, VPC CNI to compatible versions), then nodes — MNG/self-managed/Fargate are all manual since nodes aren't auto-upgraded. Skew rule: kubelet may lag the API server by up to 3 minors and must never run ahead, but I keep nodes within one minor in production. The failure I'd pre-empt is **removed APIs**: before bumping, run `kubent`/`pluto` against live manifests and Helm releases to catch deprecated beta APIs (e.g. old `Ingress`, `PodSecurityPolicy`, autoscaling betas) that the new API server will reject, which otherwise silently breaks controllers post-upgrade. I'd also stage on a non-prod cluster and watch add-on compatibility tables.

</details>

<details>
<summary><strong>Q:</strong> Your monthly AWS bill for an EKS platform jumped and EC2 didn't grow much. Where do you look?</summary>

On EKS the hidden costs are usually **data transfer**, not compute. Cross-AZ traffic is billed, so chatty service-to-service calls or `externalTrafficPolicy: Cluster` (which load-balances across all AZs) generate inter-AZ charges — I'd check VPC flow logs / Cost Explorer by usage type and enable topology-aware routing or `internalTrafficPolicy: Local` to keep traffic in-AZ. **NAT Gateway data processing** is the other big one: image pulls and outbound traffic funneled through a single NAT add up fast; I'd add ECR/S3 VPC gateway endpoints and per-AZ NATs. Then the flat **$0.10/hr per cluster** and any **extended-support surcharge** if a cluster slipped past 14 months on an old version.

</details>

<details>
<summary><strong>Q:</strong> Why does the AWS Load Balancer Controller need the EKS control plane to reach your nodes, and how does that manifest as a bug?</summary>

The controller registers **admission/mutating webhooks** (typically on port 9443) that the API server calls during `Ingress`/`Service`/`TargetGroupBinding` reconciliation, and the control plane communicates into your VPC via cross-account ENIs governed by the cluster security group. If that security group (or a custom node SG) blocks the webhook port from the control-plane source, `kubectl apply` of an Ingress hangs or times out with a webhook error, and no ALB gets created — even though the controller pods look healthy. The fix is allowing the control-plane CIDR/cluster SG to reach the webhook port on the nodes hosting the controller.

</details>

<details>
<summary><strong>Q:</strong> Design the networking for a multi-tenant EKS platform that must avoid IP exhaustion, isolate tenant traffic, and expose both L7 and L4 endpoints. (System design)</summary>

I'd size VPC subnets deliberately: large per-AZ **pod subnets separate from node subnets** via VPC CNI custom networking (`ENIConfig`), and enable **prefix delegation** so density isn't IP-bound. For isolation, use **security groups for pods** (`ENABLE_POD_ENI`) for sensitive tenants plus Kubernetes NetworkPolicies, and per-tenant namespaces with quotas. Identity is **Pod Identity** with one role per tenant SA (least privilege, reusable). Ingress: one **ALB via the LBC** with host/path routing, `target-type: ip`, WAF, and TLS from ACM for L7; **NLBs** for L4/TCP or static-IP needs. Compute is **Karpenter** with per-tenant NodePools (taints/labels) and Spot diversification, disruption budgets to protect SLAs. Add ECR/S3 VPC endpoints to cut NAT cost, topology-aware routing to cut cross-AZ, and centralize CoreDNS/observability. The scaling thresholds I'd watch are subnet IP headroom, per-node max-pods, and STS/EC2 API throttling under spiky scale.

</details>

<details>
<summary><strong>Q:</strong> A Fargate pod can't assume its IAM role even though the same setup works on EC2 nodes. What's going on?</summary>

Most likely the workload was configured for **EKS Pod Identity**, which is **not supported on Fargate** (it's Linux/EC2-only and relies on a node-level Pod Identity Agent DaemonSet that Fargate can't run). On Fargate you must use **IRSA**: ensure the cluster has an OIDC provider, the role trust policy references that OIDC issuer + the pod's namespace/SA `sub`, and the ServiceAccount carries the `eks.amazonaws.com/role-arn` annotation so the SDK does `AssumeRoleWithWebIdentity`. Also confirm the SDK version supports the credential source and the default credential chain isn't being overridden.

</details>

<details>
<summary><strong>Q:</strong> What actually happens to your cluster if you let a Kubernetes version run past the end of extended support?</summary>

A minor version has 14 months standard support, then 12 months **extended support** (billed at a higher per-cluster-hour rate, with continued security patches for the control plane and core add-ons). Past the end of extended support AWS **force-upgrades only the control plane** to the next supported version, on its own schedule and **without notice** — and it only touches the control plane: self-managed and managed node groups stay on the old version, so you can hit version-skew breakage and CrashLoops if you don't proactively refresh nodes and add-ons. You also can't create new clusters on an out-of-support version. The lesson: treat upgrades as routine quarterly work, not a "let it ride" decision.

</details>

<details>
<summary><strong>Q:</strong> (Experience) You containerized a legacy app and ran it on both EKS and ECS at UnitedHealth. How did you decide what went where, and how did you wire up identity and ingress?</summary>

I containerized Pega and ran it across EKS and ECS using ECR for images, IAM for scoped access, an ALB for L7 ingress, Route 53 for DNS, and a purpose-built VPC. ECS fit the simpler, AWS-native services where I wanted minimal orchestration overhead and tight integration with task IAM roles; EKS was for the workloads that needed real Kubernetes primitives — declarative rollouts, richer scheduling, and portability of the manifests. For identity I scoped IAM tightly per workload rather than sharing the node/instance role (the same least-privilege instinct that today maps to IRSA/Pod Identity), fronted HTTP traffic through an ALB with Route 53 records for stable endpoints, and kept image distribution in ECR close to the cluster to avoid cross-region pulls. The earlier win that made this credible was cutting the Pega install from 11 hours to 30 minutes by scripting it in Python/shell, which is what made containerizing it tractable in the first place.

</details>

<details>
<summary><strong>Q:</strong> (Experience) You've done large multi-region infra with Terraform at Oracle. How does that experience translate to running EKS at scale across regions?</summary>

At Oracle I cut region build time from 30 days to 8 hours with Terraform and rolled changes across 34 regions in 4 phases via ARM, which is exactly the discipline EKS-at-scale needs: clusters, node groups, IAM (OIDC/Pod Identity), VPC/subnet sizing, and add-ons all defined as code and promoted region-by-region with health checks and guardrails — never a big-bang. The Redis live-migration work (8-step sequencing with health-checks and guardrails that cut the state tier 68.4%) is the same playbook I'd use for an EKS minor-version upgrade or a node-group/prefix-delegation cutover: staged, reversible, health-gated steps rather than in-place mutation. And the on-call reduction from 10+/week to zero by hardening management APIs with RBAC, IP restrictions, and mTLS maps directly to least-privilege Pod Identity, security groups for pods, and locked-down control-plane access on EKS.

</details>

## Say it with your resume

- **Containerized Pega onto AWS EKS & ECS** with ECR, IAM, ALB, Route 53, and a custom VPC at UnitedHealth — direct, hands-on experience with the exact services in this topic (managed K8s + core AWS networking/identity).
- **Cut Pega install 11h → 30min** via Python/shell automation — the kind of bootstrap automation that makes containerization and repeatable node provisioning tractable.
- **Multi-region IaC with Terraform at Oracle** (30d → 8h region builds, ARM rollout across 34 regions in 4 phases) — the staged, guardrailed promotion model that EKS cluster/node-group/add-on management demands at scale.
- **8-step Redis live-migration** (sequencing, health-checks, guardrails; state tier −68.4%, 357 cores) — the same reversible, health-gated playbook used for EKS version upgrades and prefix-delegation/node-group cutovers.
- **On-call 10+/wk → 0 via secure management APIs** (RBAC, IP restrictions, mTLS) — the least-privilege, locked-down-access instinct behind IRSA/Pod Identity, security groups for pods, and restricted EKS control-plane access.

## Sources

- [What is Amazon EKS?](https://docs.aws.amazon.com/eks/latest/userguide/what-is-eks.html)
- [EKS Pod Identity grants pods access to AWS services](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html)
- [IAM roles for service accounts (IRSA)](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html)
- [Assign more IP addresses to Amazon EKS nodes with prefixes](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html)
- [Kubernetes version lifecycle on EKS (standard/extended support, skew)](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html)
- [AWS Load Balancer Controller (Helm install)](https://docs.aws.amazon.com/eks/latest/userguide/lbc-helm.html)
- [Karpenter NodePools / EC2NodeClass on EKS](https://karpenter.sh/docs/)
- [Amazon VPC CNI plugin (max-pods, WARM targets)](https://github.com/aws/amazon-vpc-cni-k8s/blob/master/README.md)
