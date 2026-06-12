---
title: Kubernetes
bucket: tech
sources: https://kubernetes.io/docs/concepts/
depth: standard
added: 2026-06-08
generated: true
---

## Core concepts

### Mechanism / internals

**The reconcile model is the whole system.** Kubernetes is a set of controllers running level-triggered (not edge-triggered) reconcile loops: each watches desired state in `etcd` (via the API server), observes actual state, and acts to close the gap — then repeats forever. There is no transaction or "apply once" semantics; a controller that misses an event still converges on its next resync because it compares full state, not deltas. This is why Kubernetes self-heals and why `kubectl apply` is declarative rather than imperative.

**Control plane components:**
- **API server** — the only component that talks to etcd. Stateless, horizontally scalable, does authn/authz/admission/validation, then persists. All other components are clients that watch and write through it. Admission webhooks (mutating then validating) run here and are a common source of cluster-wide outages when their backing service is down and `failurePolicy: Fail`.
- **etcd** — a Raft-based strongly-consistent KV store. Quorum (majority of an odd-sized member set) is required for writes; lose quorum and the cluster goes read-only. It is latency-sensitive (fsync to disk on every write) — slow disks manifest as API-server-wide slowness. Watch out for the default DB size limit and history compaction.
- **scheduler** — runs a two-phase loop per pending pod: **Filter** (predicates: does the node have enough requested CPU/mem, matching node selectors/affinity, tolerated taints, available ports?) producing the set of *feasible* nodes, then **Score** (priorities: spread, least/most-allocated, affinity weight) to rank them; highest score wins, ties broken randomly. Implemented as the **scheduling framework** with pluggable extension points (`QueueSort`, `Filter`, `Score`, `Reserve`, `Permit`, `Bind`). If filtering returns an empty set, the pod stays **Pending** and is retried as cluster state changes. ([kube-scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/))
- **controller-manager** — bundles the built-in controllers (Deployment, ReplicaSet, Node, Job, endpoint/EndpointSlice, etc.), each a reconcile loop. **kubelet** on each node is the node-level reconciler: it owns pod lifecycle, runs probes, reports status, and performs node-pressure eviction.

**Workload controllers:**
- **Deployment → ReplicaSet → Pods.** A Deployment manages ReplicaSets; a rollout creates a new RS and shifts replicas governed by `maxSurge`/`maxUnavailable`. Rollback just scales an old RS back up (history kept via `revisionHistoryLimit`). ([Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/))
- **StatefulSet** — stable network identity and ordered, one-at-a-time create/update/delete (`OrderedReady`), each pod with its own PVC. `partition` in `RollingUpdate` enables canary/phased rollouts; `kubectl patch sts ... partition: 0` finishes the roll. ([StatefulSet basics](https://kubernetes.io/blog/2017/09/kubernetes-statefulsets-daemonsets/))
- **DaemonSet** — one pod per (matching) node, scheduled via node affinity + tolerations rather than the replica count.

**Networking:** every pod gets a routable IP (the CNI plugin wires this up; the API has no built-in network). A **Service** is a stable virtual IP backed by **EndpointSlices**; **kube-proxy** programs the data path — in `iptables` mode it installs DNAT rules that randomly load-balance across endpoints (`KUBE-SVC-*` → `KUBE-SEP-*`), in `ipvs` mode it uses kernel IPVS for better scale. **Ingress**/Gateway API handle L7 HTTP routing via a controller (nginx, ALB, etc.). **CoreDNS** provides service discovery. ([debug-service](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/))

**Probes:** `startupProbe` gates the others (use it for slow-starting apps so liveness doesn't kill them during boot); `livenessProbe` failure restarts the container; `readinessProbe` failure pulls the pod out of Service endpoints without restarting it. ([Probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/))

**Resources & QoS:** `requests` drive scheduling and the cgroup CPU share; `limits` are the hard ceiling enforced by the kernel. QoS class is derived: **Guaranteed** (requests == limits for every container, both CPU and memory), **Burstable** (at least one request set but not equal), **BestEffort** (nothing set). QoS dictates eviction order. ([resource-managers](https://kubernetes.io/docs/concepts/workloads/resource-managers/))

### Trade-offs

- **`iptables` vs `ipvs` kube-proxy:** iptables is simple and ubiquitous but rule evaluation is O(n) — thousands of Services degrade connection setup; ipvs scales to large clusters with hash-table lookups at the cost of needing kernel modules.
- **Requests = limits (Guaranteed) vs Burstable:** Guaranteed gives predictable performance and last-to-evict status, but you pay for headroom you may not use and lose burst capacity. Burstable improves bin-packing/density but invites noisy-neighbor and OOM risk.
- **StatefulSet ordered rollout vs Deployment:** ordered guarantees safe quorum changes for stateful systems (databases, Kafka) but is slow and serial; Deployments roll fast in parallel but assume fungible, stateless pods.
- **HPA vs VPA vs Karpenter/Cluster Autoscaler:** HPA scales replica count horizontally (good for stateless throughput); VPA right-sizes requests/limits but must restart pods to apply (conflicts with HPA on the same metric); node autoscalers (Cluster Autoscaler/Karpenter) add/remove *nodes* — you almost always need pod-level + node-level autoscaling together.
- **Soft vs hard eviction thresholds:** soft gives a grace period for graceful shutdown but reacts slower; hard reclaims immediately with 0s grace (and ignores PDBs and `terminationGracePeriodSeconds`).

### Failure modes / gotchas

- **CrashLoopBackOff:** container keeps exiting (bad config, missing dependency, failing liveness probe, OOM). Kubelet applies exponential backoff up to 5 min. A too-aggressive liveness probe (short `timeoutSeconds`/`failureThreshold`) will *cause* crash loops under load — liveness is for deadlock, not slowness.
- **Readiness flapping:** a readiness probe that depends on a downstream (DB) means a downstream blip yanks all pods out of rotation simultaneously → cascading outage. Keep readiness checks local.
- **OOMKilled vs eviction:** OOMKilled is a *kernel* cgroup event (container exceeded its memory limit) — sudden, no grace, container restarts in place. Node-pressure **eviction** is the *kubelet* reclaiming node resources by deleting pods (BestEffort first, then Burstable by priority/usage, Guaranteed last), setting pod phase to `Failed`. ([node-pressure-eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/))
- **CPU throttling:** CPU limits are enforced by CFS quota; even a pod well under its average can be throttled in bursts, adding tail latency. Many teams set CPU requests but drop CPU limits to avoid throttling.
- **Pending pods:** insufficient resources, unsatisfiable affinity/topology spread, taints without tolerations, no PV available, or scheduler can't fit it — `kubectl describe pod` Events tell you which.
- **DNS:** CoreDNS overload or `ndots:5` search-domain amplification causes mysterious latency; ImagePull failures (`ErrImagePull`/`ImagePullBackOff`) from bad creds, missing `imagePullSecrets`, or rate-limited registries.
- **Admission webhook outage** with `failurePolicy: Fail` can block all writes cluster-wide.
- **PDB deadlock:** a PodDisruptionBudget with `minAvailable` too tight blocks voluntary disruptions (node drains/upgrades) indefinitely.

### Tuning knobs

- Rollout: `maxSurge`/`maxUnavailable` (`kubectl patch deployment ... rollingUpdate`), `minReadySeconds`, `progressDeadlineSeconds`, `revisionHistoryLimit`.
- Probes: `initialDelaySeconds`, `periodSeconds`, `timeoutSeconds`, `failureThreshold`, plus `startupProbe.failureThreshold * periodSeconds` as the slow-start budget.
- Scheduling: `topologySpreadConstraints` (`maxSkew`, `topologyKey`, `whenUnsatisfiable`), taints/tolerations, node/pod affinity weights, `priorityClassName`, scheduler profiles.
- Resources: requests/limits per container, LimitRange/ResourceQuota per namespace, QoS via requests==limits.
- Autoscaling: HPA `behavior` (scale-up/down stabilization windows + policies), VPA update mode.
- Eviction: `--eviction-hard`/`--eviction-soft`/`--eviction-soft-grace-period` on kubelet.

## Interview questions

<details>
<summary><strong>Q:</strong> Explain why Kubernetes uses a level-triggered reconcile model instead of acting on events, and what that buys you operationally.</summary>

Controllers don't process a stream of deltas; each loop reads the *full* desired and observed state and acts to close the gap, then resyncs periodically. Because it's level-triggered, a controller that crashes, misses a watch event, or restarts still converges on the next pass — there's no "lost message" failure mode you'd get with edge-triggered systems. The trade-off is eventual (not instantaneous) consistency and idempotent, restartable controllers. This is also why `kubectl apply` is declarative: you describe the end state and the system continuously drives toward it rather than running one-shot commands.

</details>

<details>
<summary><strong>Q:</strong> Walk me through what the scheduler actually does between a pod being created and landing on a node. What makes it stay Pending?</summary>

The scheduler runs a per-pod loop with two phases. **Filter** runs predicates — does the node have enough of the pod's requested CPU/memory, do node selectors/affinity match, are the node's taints tolerated, are required ports free, is a PV bindable — producing the set of *feasible* nodes. **Score** ranks the feasible set with priorities (spread, least-allocated, affinity weight); highest wins, ties random. It then binds the pod (writes `nodeName`). A pod stays **Pending** when filtering returns an empty set — no node has room, an affinity/topology-spread rule is unsatisfiable, or a taint isn't tolerated. The scheduler retries as the cluster changes (resources freed, nodes added). `kubectl describe pod` Events name the exact failing predicate. ([kube-scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/))

</details>

<details>
<summary><strong>Q:</strong> A pod is stuck in CrashLoopBackOff. Walk me through your diagnosis.</summary>

`kubectl describe pod` and check the container's last state and exit code; `kubectl logs --previous` to see the crashed instance's output. Exit code 137 + reason OOMKilled means it hit its memory limit — raise the limit or fix the leak. A nonzero app exit usually means bad config, a missing dependency/secret/mount, or a failing migration on startup. Critically, check whether a too-aggressive *liveness* probe is killing a healthy-but-slow container — short `timeoutSeconds`/`failureThreshold` under load causes self-inflicted restarts; the fix is a `startupProbe` to cover boot and relaxed liveness timing. Kubelet applies exponential backoff (capped at 5 min), so "BackOff" itself is just the restart delay, not the root cause.

</details>

<details>
<summary><strong>Q:</strong> Distinguish liveness, readiness, and startup probes — and give me a failure mode for each that you've actually had to reason about.</summary>

Liveness restarts the container on failure (recover from deadlock); readiness removes the pod from Service endpoints without restarting (back off traffic during transient unreadiness); startup gates the other two so slow-booting apps aren't killed mid-startup. Failure modes: an over-tight *liveness* probe restart-loops a healthy app under load. A *readiness* probe that checks a shared downstream (DB) pulls *every* replica out of rotation when that downstream blips — a cascading outage; keep readiness local. Missing a *startup* probe on a JVM/heavy app means liveness fires during the long boot and the pod never comes up. ([Probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/))

</details>

<details>
<summary><strong>Q:</strong> How are QoS classes derived, and why does it matter beyond scheduling?</summary>

QoS is computed from requests/limits: **Guaranteed** when every container sets requests == limits for both CPU and memory; **Burstable** when at least one request is set but not equal; **BestEffort** when none are set. It matters most under node pressure: the kubelet evicts BestEffort first, then Burstable (ordered by priority and how far over requests they're running), and Guaranteed last. Guaranteed pods also get exclusive CPUs under the static CPU manager policy and clean topology hints from the memory manager. The trade-off is density vs predictability — Guaranteed wastes reserved headroom but protects latency-critical workloads. ([resource-managers](https://kubernetes.io/docs/concepts/workloads/resource-managers/))

</details>

<details>
<summary><strong>Q:</strong> A latency-sensitive service is showing p99 spikes even though its CPU usage is well below its limit. What's likely happening?</summary>

Almost certainly CFS CPU throttling. CPU limits are enforced as a quota per 100 ms period; a bursty workload can exhaust its quota mid-period and get throttled even when its *average* utilization looks low, producing exactly those tail-latency spikes. Confirm with `container_cpu_cfs_throttled_periods_total`. Fixes: raise or remove the CPU limit (keep the request for scheduling), reduce per-period burstiness, or tune the cgroup period. Many teams deliberately set CPU requests but no CPU limits for latency-critical services for this reason — memory limits stay because OOM is a correctness issue, CPU throttling is a performance one.

</details>

<details>
<summary><strong>Q:</strong> OOMKilled versus a kubelet node-pressure eviction — what's the difference and how do you tell them apart?</summary>

OOMKilled is a kernel cgroup event: a container exceeded *its own* memory limit, the kernel OOM killer reaps it, the container restarts in place, and the pod status shows reason `OOMKilled` (exit 137). Node-pressure eviction is the *kubelet* reclaiming whole-node resources when an eviction signal (e.g. `memory.available`) crosses a threshold — it deletes pods (BestEffort → Burstable → Guaranteed, by priority within class), sets phase to `Failed`, and the controller reschedules them elsewhere. Hard thresholds give 0s grace and ignore PDBs and `terminationGracePeriodSeconds`. Tell-tale: OOMKilled is in the container's terminated state; eviction shows a pod-level `Evicted` status with a node-pressure message. ([node-pressure-eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/))

</details>

<details>
<summary><strong>Q:</strong> How does a Deployment rollout actually move traffic, and how do maxSurge/maxUnavailable interact with PodDisruptionBudgets?</summary>

A Deployment owns multiple ReplicaSets; a rollout creates a new RS and shifts replicas — `maxSurge` allows extra pods above desired (faster, needs spare capacity), `maxUnavailable` allows fewer ready pods (no spare capacity needed, briefly reduced capacity). Setting both to safe values bounds the blast radius. PDBs constrain *voluntary* disruptions like node drains, not rollouts directly — but during an upgrade a too-strict `minAvailable` can block the drain entirely, deadlocking the maintenance. Rollback is cheap: the old RS still exists (`revisionHistoryLimit`), so `kubectl rollout undo` just scales it back up. ([Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/))

</details>

<details>
<summary><strong>Q:</strong> When do you reach for a StatefulSet over a Deployment, and how do you do a safe canary rollout of one?</summary>

StatefulSet when pods are not fungible — stable identity (`pod-0`, `pod-1`), stable per-pod storage (PVC per pod), and ordered, one-at-a-time lifecycle. That's databases, Kafka, ZooKeeper, anything where quorum and identity matter. For a canary, use the `RollingUpdate` `partition`: set partition to N so only ordinals >= N update; verify the canary, then lower the partition stepwise to 0 to finish (`kubectl patch sts kafka -p '{"spec":{"updateStrategy":{"rollingUpdate":{"partition":0}}}}'`). The cost is that ordered serial updates are slow — you trade rollout speed for the safety stateful systems require. ([StatefulSets](https://kubernetes.io/blog/2017/09/kubernetes-statefulsets-daemonsets/))

</details>

<details>
<summary><strong>Q:</strong> Trace a packet from a client hitting a ClusterIP Service to a backend pod. Where does load balancing happen, and what breaks at scale?</summary>

The client resolves the Service name via CoreDNS to the stable ClusterIP. kube-proxy has programmed the data path: in `iptables` mode, the ClusterIP DNAT rule (`KUBE-SERVICES` → `KUBE-SVC-*`) randomly picks an EndpointSlice member (`KUBE-SEP-*`) using `-m statistic --mode random --probability`, rewriting the destination to a pod IP that the CNI made routable. No userspace hop. At scale, iptables rule evaluation is O(n) — tens of thousands of Services/endpoints slow connection setup and rule reloads; switch kube-proxy to `ipvs` mode (kernel hash-table lookups) or use an eBPF dataplane. Also watch EndpointSlice churn during big rollouts. ([debug-service](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/))

</details>

<details>
<summary><strong>Q:</strong> How do taints/tolerations, node affinity, and topology spread constraints differ in intent, and when do you combine them?</summary>

They answer different questions. **Taints/tolerations** are repulsion from the node's side — a node says "only pods that tolerate me may land here" (dedicated GPU nodes, control-plane nodes). **Node affinity** is attraction from the pod's side — "I want nodes with this label." **Topology spread constraints** control *distribution* — spread my replicas across zones/nodes with a bounded `maxSkew` and `whenUnsatisfiable: DoNotSchedule|ScheduleAnyway`. You combine them on, say, a multi-AZ HA service: node affinity to land on app nodes, a toleration for a dedicated taint, and topology spread across zones so a single-AZ failure can't take out a quorum. ([topology-spread](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/))

</details>

<details>
<summary><strong>Q:</strong> Compare HPA, VPA, and node autoscaling. Why can't HPA and VPA both manage CPU on the same workload?</summary>

HPA scales replica *count* on observed metrics (CPU, custom, external) — right for stateless throughput. VPA right-sizes per-pod requests/limits but must evict/restart pods to apply new values. Node autoscalers (Cluster Autoscaler, Karpenter) add/remove *nodes* when pods can't be scheduled or nodes are underused. HPA and VPA conflict when both target the same resource metric: VPA changes requests, which moves the per-pod utilization HPA divides by, so they fight and oscillate. The standard pattern is HPA on CPU/RPS for horizontal scale, VPA in recommendation-only mode or on memory, plus a node autoscaler underneath — you need both pod- and node-level elasticity, not one.

</details>

<details>
<summary><strong>Q:</strong> Design a multi-AZ, highly-available 3-tier app on Kubernetes. Walk through the key resource choices.</summary>

Stateless web/API tiers as Deployments with `topologySpreadConstraints` across zones (`maxSkew: 1`, `DoNotSchedule`) so no AZ holds a quorum, fronted by a Service + Ingress/ALB and HPA on RPS/CPU. State tier (DB/cache) as a StatefulSet with PVCs, anti-affinity across nodes/zones, and ordered updates via `partition` for safe canaries. Protect availability with PodDisruptionBudgets (`minAvailable` sized so a node drain or AZ loss never breaks quorum), `priorityClassName` so critical pods evict less-critical ones under pressure, and readiness probes that are *local* to avoid cascading flaps. Underneath: a node autoscaler for elasticity and resource requests set so the scheduler bin-packs without overcommit. Networking via CNI with NetworkPolicies isolating tiers.

</details>

<details>
<summary><strong>Q:</strong> You migrated a stateful service (e.g. a Redis tier) into Kubernetes/EKS with a strict cutover sequence. How do you design the live migration to be safe?</summary>

This maps directly to the 8-step Redis live-migration I ran at Oracle. The principles port cleanly: enforce strict *sequencing* (don't touch the next node until the current one is verified), gate every step on *health checks* — readiness must reflect actual replication/quorum state, not just process-up — and put *guardrails* in front of irreversible actions (drain confirmations, PDBs that block draining below quorum, automated rollback if a health gate fails). On Kubernetes I'd model the tier as a StatefulSet with ordered updates and `partition`-based canaries, use PDBs to make voluntary disruptions respect quorum, and drive the cutover through Terraform/Jenkins so the sequence is repeatable and auditable. That discipline is what let me cut the state tier 68.4% without an outage.

</details>

<details>
<summary><strong>Q:</strong> At UnitedHealth you containerized Pega onto EKS/ECS. How did you decide what ran where, and what production guardrails did you put around the cluster?</summary>

The split was workload-shape driven: long-lived stateful and orchestration-heavy components went to EKS where I had StatefulSets, PDBs, affinity, and HPA; simpler stateless task-style services fit ECS. On EKS the guardrails were RBAC scoped to per-team ServiceAccounts (least privilege, no shared cluster-admin), ResourceQuota/LimitRange per namespace to stop one tenant starving the cluster, requests/limits set for sane QoS and bin-packing, readiness/liveness/startup probes tuned to Pega's slow boot, and Ingress/ALB + Route 53 for routing with IAM/VPC isolation underneath. Image supply came from ECR with pull credentials via ServiceAccount, and everything was provisioned through Terraform so the cluster config was reviewed and reproducible.

</details>

## Say it with your resume

- **Oracle Redis live-migration (8 steps, strict sequencing + health checks + guardrails, state tier cut 68.4%):** the exact discipline a senior engineer needs for StatefulSet rollouts, partition-based canaries, and PDB-gated drains — sequence, verify on real health signals, guard the irreversible step, roll back on failure.
- **UnitedHealth: containerized Pega onto AWS EKS & ECS, ECR, IAM, ALB, Route 53, VPC:** end-to-end ownership of cluster networking (Service/Ingress/ALB + Route 53), image supply (ECR + ServiceAccount pull creds), and identity boundaries (IAM/RBAC/VPC) — not just deploying pods.
- **3-tier HA app (Docker Swarm + Ansible):** the multi-AZ, anti-affinity, quorum-aware HA design translates directly to topology spread constraints, PDBs, and zone-aware StatefulSets in Kubernetes.
- **ARM across 34 regions, control planes:** large-scale, multi-region control-plane operation — the scaling concerns (etcd latency, API server load, scheduler throughput, kube-proxy mode at scale) are exactly the senior failure modes above.
- **Terraform + Jenkins:** cluster and workload config as reviewed, reproducible IaC with CI-driven rollouts — the auditable, repeatable delivery a staff engineer is expected to own.

## Sources

- [Kubernetes Concepts](https://kubernetes.io/docs/concepts/)
- [Kubernetes Scheduler](https://kubernetes.io/docs/concepts/scheduling-eviction/kube-scheduler/)
- [Node-pressure Eviction](https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/)
- [Pod Lifecycle: Probes](https://kubernetes.io/docs/concepts/workloads/pods/probes/)
- [Resource Managers / QoS](https://kubernetes.io/docs/concepts/workloads/resource-managers/)
- [Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/)
- [StatefulSets and DaemonSets](https://kubernetes.io/blog/2017/09/kubernetes-statefulsets-daemonsets/)
- [Pod Topology Spread Constraints](https://kubernetes.io/docs/concepts/scheduling-eviction/topology-spread-constraints/)
- [Debugging Services](https://kubernetes.io/docs/tasks/debug/debug-application/debug-service/)
