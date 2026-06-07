---
title: Kubernetes
bucket: tech
must: true
gap: false
rank: 3
sources: https://kubernetes.io/docs/concepts/
generated: true
---

## 80/20 — Core concepts

- **Pod** — smallest deployable unit; one or more co-located containers sharing a network namespace (one IP) + storage. Ephemeral; usually not created directly.
- **Deployment → ReplicaSet → Pods** — a ReplicaSet keeps N identical Pods running; a Deployment owns ReplicaSets and adds rolling updates + rollbacks. StatefulSet for stable identity/storage, DaemonSet for one-pod-per-node.
- **Declarative reconcile loop** — you submit desired state to the API server (stored in etcd); controllers continuously compare desired vs. actual and converge. Control plane = API server + etcd + scheduler + controller-manager; nodes run kubelet + runtime + kube-proxy.
- **Service** — stable virtual IP/DNS load-balancing across label-selected Pods. Types: `ClusterIP` (internal default), `NodePort`, `LoadBalancer`; `Ingress` for L7 HTTP/TLS.
- **Networking** — every Pod gets a routable IP; all Pods reach each other without NAT. A **CNI** implements pod networking; kube-proxy programs Service VIP → endpoint routing.
- **Scaling** — `kubectl scale` for manual; **HorizontalPodAutoscaler** (`autoscaling/v2`) adjusts replicas on CPU/memory/custom metrics within min/max. With multiple metrics it scales to the most demanding.

## Likely interview questions

**Q:** Pod vs. Deployment vs. ReplicaSet?
**A:** A Pod is the runtime unit (containers + shared net/storage). A ReplicaSet ensures N identical Pods exist. A Deployment owns ReplicaSets and adds declarative rolling updates/rollbacks — you almost always create a Deployment, not bare Pods.

**Q:** How does the reconcile loop / controller pattern work?
**A:** Controllers watch the API server for desired state and continuously drive actual toward it. If a Pod dies, the ReplicaSet controller sees the gap and creates a replacement — convergence is continuous, not a one-time apply.

**Q:** How do Services route to Pods, and what are the types?
**A:** A Service selects Pods by label and gives a stable ClusterIP; kube-proxy/CNI load-balance to healthy endpoints. ClusterIP is internal, NodePort exposes a port on every node, LoadBalancer provisions a cloud LB, Ingress does L7 routing/TLS.

**Q:** How does the HPA decide to scale?
**A:** It compares an observed metric (e.g. CPU vs. a 50% target) to the target, computes desired replicas, bounded by min/max. With multiple metrics it scales to satisfy the most demanding one.

## Say it with your resume

- **Hook:** your UnitedHealth EKS/ECS containerization work is your hands-on Kubernetes story — containerized workloads, orchestration, scaling on a managed cluster.
- Bridge to your scale narrative: the **34-region rollout** and **8-step live-migration with health checks + guardrails** show you think in terms of *desired state, health, and safe convergence* — exactly the reconcile-loop mindset.

## Sources

- [Kubernetes Concepts](https://kubernetes.io/docs/concepts/)
