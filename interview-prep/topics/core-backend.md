---
title: Core Backend (Java & Python)
bucket: tech
must: false
rank: 10
sources: https://docs.oracle.com/en/java/javase/21/
depth: standard
generated: true
---

## Core concepts

### JVM memory & GC
The JVM splits storage into the **per-thread stack** (frames, locals, return addresses — fast, no GC, sized by `-Xss`) and the **shared heap** (objects, GC-managed). The mainstream collectors are **generational** because of the weak generational hypothesis: most objects die young. The heap is split into a **young generation** (Eden + two survivor spaces) and an **old generation**; cheap **minor GCs** copy survivors between survivor spaces and promote long-lived objects to old gen, while **major/full GCs** are rarer and more expensive. **G1** (default since JDK 9, JEP 248) divides the heap into ~2048 equal-size *regions* and does mostly-concurrent marking with incremental evacuation, targeting a *soft* pause goal (`-XX:MaxGCPauseMillis`, default 200ms) — pauses scale with the volume of *live* data it must copy in a collection. **ZGC** (JEP 377, generational since JDK 21 via JEP 439) is a concurrent, region-based collector using *colored pointers* and *load barriers* that does almost all work concurrently with the application, advertising **sub-millisecond max pause times** independent of heap size (8MB–16TB) [openjdk.org/projects/zgc]. Trade-off: G1 gives the best **throughput** for most batch/request workloads and a smaller footprint; ZGC trades some throughput and CPU/footprint overhead for consistently low **tail latency** — pick ZGC when p99/p999 pause sensitivity dominates (low-latency services, large heaps). **Failure mode:** GC pauses are stop-the-world stalls; allocation pressure (high young-gen churn) drives frequent minor GCs, while a leak or undersized old gen drives the classic spiral of back-to-back full GCs ("GC thrashing") where the app spends most CPU collecting and effectively hangs before `OutOfMemoryError`.

### Java concurrency (incl. virtual threads)
Platform threads are thin wrappers over OS threads — scarce, ~1MB stack each, expensive to create — so we pool them via `ExecutorService`. Correctness across threads is governed by the **Java Memory Model**: without synchronization, one thread's writes are not guaranteed visible to another. The JMM defines a **happens-before** partial order — a `volatile` write happens-before a subsequent read of the same field, unlocking a monitor happens-before locking it, `Thread.start()` happens-before the thread's first action — and only when a happens-before edge exists are writes guaranteed visible and free of reordering hazards. **Virtual threads** (JEP 444, final in JDK 21, Project Loom) are JVM-scheduled user-mode threads multiplexed onto a small pool of **carrier** platform threads. When a virtual thread hits a blocking call (e.g. socket read) it **unmounts** from its carrier, freeing the OS thread to run another virtual thread; it remounts when ready. Crucially, *"virtual threads are not faster threads... they exist to provide scale (higher throughput), not speed (lower latency)"* — you can run **millions** of them, making the simple blocking **thread-per-request** style scale like async/reactive code without the callback complexity [docs.oracle.com]. This is why they change blocking-IO scaling: blocking a virtual thread is cheap, so you stop needing thread pools sized to your I/O concurrency. **Failure mode — pinning:** a virtual thread inside a `synchronized` block/method or a `native`/FFI frame is *pinned* and cannot unmount, blocking the underlying carrier OS thread; the classic fix is to replace contended `synchronized` with `ReentrantLock` (JDK 24/JEP 491 later removes most synchronized pinning).

### Python concurrency & the GIL
The **GIL** is a mutex in CPython that *"ensures only one thread executes Python bytecode at a time"*, which makes the object model (notably reference-count updates) implicitly thread-safe but caps CPU parallelism on multicore [docs.python.org glossary]. What it *protects*: bytecode execution and refcount integrity. What it does **not** give you: atomicity of compound operations, or any CPU speedup from threads. CPython releases the GIL around blocking I/O and inside C extensions that opt out (NumPy, hashlib), which is why **threading still helps I/O-bound** work. The decision tree: **I/O-bound** → `asyncio` (single thread, cooperative scheduling, scales to tens of thousands of sockets with low overhead) or a thread pool; **CPU-bound** → `multiprocessing` / `ProcessPoolExecutor` to get true parallelism across separate interpreters and address spaces (paying IPC/pickle and memory cost). Python 3.13 ships an experimental **free-threaded** build (`--disable-gil`, PEP 703) that removes this ceiling. **Memory:** CPython uses **reference counting** as primary reclamation, plus a **cyclic GC** with **three generations** that detects reference cycles refcounting alone can't free; you can `gc.disable()` if you guarantee no cycles, or call `gc.collect()` to force a sweep [docs.python.org gc].

### Perf failure modes & tuning
**N+1 queries** — one query per row instead of a join/batch — is the most common backend latency killer; fix with eager loading / `IN` batching. **Allocation pressure** (short-lived garbage in hot loops) inflates minor-GC frequency; Java **escape analysis** mitigates this by proving an object never escapes a method/thread and scalar-replacing or stack-allocating it, so allocation-free hot paths and minimizing per-request object churn pay off. **Blocking the event loop** — calling synchronous I/O or a CPU-heavy function inside a coroutine — stalls *every* coroutine; offload via `asyncio.to_thread()` (I/O) or `loop.run_in_executor(ProcessPoolExecutor, ...)` (CPU) [docs.python.org]. **Resource leaks**: Java **try-with-resources** (`AutoCloseable`, deterministic close in reverse order) and Python **context managers** (`with` / `__enter__`/`__exit__`) guarantee release on the exception path — relying on `finalize()`/`__del__` is non-deterministic and tied to GC timing. **Data-structure complexity** matters under load: `HashMap`/`dict` O(1) average but O(n) on pathological collisions; `ArrayList`/`list` O(1) amortized append but O(n) middle insert; prefer `ArrayDeque`/`collections.deque` for queue ops.

## Interview questions

<details>
<summary><strong>Q:</strong> Walk me through what physically happens during a G1 collection, and how that differs from ZGC. When would you switch a service from G1 to ZGC?</summary>

G1 partitions the heap into ~2048 equal regions and runs concurrent marking to find live data, then does incremental, mostly stop-the-world *evacuation*: it copies live objects out of the regions with the most garbage into fresh regions and reclaims the old ones, aiming for a soft pause target (`MaxGCPauseMillis`, default 200ms). Its pauses scale with the volume of live data it copies, so a large live set or high promotion rate lengthens pauses. ZGC does evacuation *concurrently* using colored pointers and load barriers so the application keeps running, giving sub-millisecond max pauses largely independent of heap size. I'd switch to ZGC when tail latency (p99/p999) is the SLO and G1 pauses are bleeding through — large heaps, low-latency request paths — accepting ZGC's higher CPU/footprint overhead and slightly lower peak throughput as the cost.

</details>

<details>
<summary><strong>Q:</strong> A virtual thread is "blocked" but you still see an OS thread stuck and throughput collapsing under load. What's happening and how do you confirm it?</summary>

That's **pinning**: the virtual thread is inside a `synchronized` block/method or a native/FFI frame when it hits the blocking call, so it can't unmount from its carrier and holds the OS thread hostage. With a small carrier pool, a handful of pinned threads starves everything else and throughput falls off a cliff. I'd confirm with `-Djdk.tracePinnedThreads=full` (or JFR `jdk.VirtualThreadPinned` events) to get the exact stack, then replace the contended `synchronized` with a `ReentrantLock` (lock/try-finally/unlock), since locks let the carrier be released. On JDK 24+ (JEP 491) most synchronized pinning is gone, but native frames still pin.

</details>

<details>
<summary><strong>Q:</strong> Explain happens-before. Show a concrete bug that arises from its absence.</summary>

Happens-before is the JMM's partial order that guarantees memory visibility and ordering between actions: if A happens-before B, A's writes are visible to B and can't be reordered past it. Edges come from `volatile`, monitor lock/unlock, `Thread.start`/`join`, and `final` field semantics — without such an edge there is *no* visibility guarantee, even on x86. Classic bug: a `boolean running` flag toggled by one thread and polled in another thread's loop without `volatile` — the reader may cache it in a register and loop forever, because there's no happens-before edge forcing it to re-read main memory.

```java
// broken: no happens-before -> reader may never see the write
private boolean running = true;            // make it volatile to fix
public void stop() { running = false; }
public void run() { while (running) { /* ... */ } }
```

</details>

<details>
<summary><strong>Q:</strong> Exactly what does the GIL protect, and what does it not? Give an example of a race that the GIL does NOT prevent.</summary>

The GIL serializes execution of Python bytecode so only one thread runs the interpreter at a time, which keeps reference counts and the object model internally consistent — that's all it guarantees. It does **not** make compound, multi-bytecode operations atomic. `counter += 1` compiles to load/add/store; the interpreter can switch threads between those bytecodes, so concurrent increments lose updates. You still need a `threading.Lock`. The GIL also gives you no CPU parallelism — it's the reason CPU-bound threading doesn't speed up — but it's released around blocking I/O and inside cooperative C extensions, which is why threads help I/O-bound work.

</details>

<details>
<summary><strong>Q:</strong> For a service doing thousands of concurrent outbound HTTP calls, compare threads, asyncio, and multiprocessing in Python. Which do you pick and why?</summary>

That workload is I/O-bound, so the GIL isn't the bottleneck — the goal is cheap concurrency for sockets that mostly wait. `asyncio` is the strongest fit: a single thread with an event loop scales to tens of thousands of in-flight requests with minimal per-task memory and no thread-context-switch overhead, given an async HTTP client. A thread pool also works and is simpler to bolt onto existing blocking code, but per-thread stacks and context switches cap you in the low thousands. `multiprocessing` is the wrong tool here — its value is bypassing the GIL for CPU parallelism, and it adds IPC/pickling and per-process memory cost that buys nothing for I/O. So: asyncio for greenfield/high fan-out, threads when wrapping legacy blocking libraries.

</details>

<details>
<summary><strong>Q:</strong> Your async Python service intermittently freezes — all requests stall together for a few hundred ms, then recover. Diagnose.</summary>

A correlated stall across *all* coroutines points to the event loop being blocked by a synchronous call on the loop thread — a CPU-heavy function, a blocking DB/file call, or even `time.sleep`/`requests` inside a coroutine. Because asyncio is cooperative and single-threaded, one un-yielding call freezes everything until it returns. I'd enable `loop.slow_callback_duration` / asyncio debug mode to log the offending callback, then offload it: `asyncio.to_thread()` for blocking I/O or `loop.run_in_executor(ProcessPoolExecutor, ...)` for CPU-bound work, keeping the loop free to schedule. A periodic spike specifically could also be a synchronous library call hidden behind an "async" wrapper.

</details>

<details>
<summary><strong>Q:</strong> A Java service shows climbing latency and CPU pegged in GC threads, eventually OOM. How do you triage GC thrashing vs a leak vs allocation pressure?</summary>

I'd turn on GC logging (`-Xlog:gc*`) and look at the pattern: high *minor* GC frequency with healthy reclamation points to **allocation pressure** — too much short-lived garbage in hot paths — fixable by reducing per-request allocations or sizing young gen up. Old-gen occupancy that ratchets upward across full GCs and never recovers is a **leak**; I'd take a heap dump (`jmap`/JFR) and find the dominator retaining the growing set. The classic **thrash** signature is back-to-back full GCs reclaiming almost nothing while CPU sits in GC and the app stalls — that's the death spiral right before OOM. The fix depends on root cause: cap retained state, fix the leak, or right-size the heap; switching to ZGC masks pause symptoms but won't fix a leak.

</details>

<details>
<summary><strong>Q:</strong> Two threads deadlock in production. Walk me through detection and the structural fix, not just "add a timeout."</summary>

Deadlock means a cycle in the lock-wait graph — each thread holds a lock the other needs. I'd capture a thread dump (`jstack` / `kill -3`); the JVM explicitly reports "Found one Java-level deadlock" with the holder/waiter chain, naming the two locks and threads. The structural fix is **lock ordering**: impose a global order on lock acquisition so a cycle is impossible, or collapse the two locks into one coarser lock if the critical sections overlap. `tryLock` with timeout is a fallback that converts deadlock into livelock/retry, not a real fix. I'd also question whether the shared mutable state needs locking at all — sometimes immutability or a concurrent collection removes the locks entirely.

</details>

<details>
<summary><strong>Q:</strong> What is escape analysis and why does it matter for allocation-heavy Java code?</summary>

Escape analysis is a JIT optimization that proves whether an object can be observed outside the method (or thread) that created it. If it can't escape, the JIT can **scalar-replace** it — exploding its fields into registers/stack slots so no heap allocation happens at all — and can elide synchronization on objects that never escape a thread (lock elision). The payoff is reduced allocation pressure and therefore fewer minor GCs in hot loops. The practical lesson for senior code: small, locally-scoped temporary objects in hot paths are often effectively free once JIT-compiled, so micro-pooling them is usually premature; but objects that escape (stored in fields, returned, published to other threads) get real heap allocation and GC cost.

</details>

<details>
<summary><strong>Q:</strong> CPython is refcounted — so why does it ship a separate garbage collector, and when would you tune or disable it?</summary>

Reference counting frees an object the instant its count hits zero, which is deterministic and prompt, but it cannot reclaim **reference cycles** — two objects referencing each other keep each other's count above zero forever. CPython's cyclic GC exists solely to detect and break those cycles. It's generational (three generations) and triggers on allocation-minus-deallocation thresholds, walking objects to find unreachable cycles. You can `gc.disable()` in a tight, allocation-heavy phase if you're certain you create no cycles (a known latency/throughput trick for batch jobs), or tune thresholds; you can also call `gc.collect()` to force a sweep. The risk of disabling is that genuine cycles then leak until re-enabled.

</details>

<details>
<summary><strong>Q:</strong> Contrast try-with-resources and Python context managers with relying on finalizers/`__del__` for cleanup.</summary>

Both try-with-resources (Java `AutoCloseable`) and Python `with` (`__enter__`/`__exit__`) give **deterministic** cleanup: the resource is closed at the end of the block, in reverse order of acquisition, *including* on the exception path, and try-with-resources adds suppressed-exception handling so a close failure doesn't mask the original error. Finalizers (`Object.finalize`, now deprecated) and `__del__` run at GC's discretion — possibly never, possibly long after the resource is exhausted — so leaning on them for file handles, sockets, or DB connections invites fd/connection exhaustion under load. The senior rule: ownership of a resource = a `with`/try-with-resources block at the right scope; finalizers are at best a safety-net log, not a cleanup mechanism.

</details>

<details>
<summary><strong>Q:</strong> Design a high-throughput, I/O-bound service (lots of downstream calls per request) in Java 21. Now contrast the Python design.</summary>

In Java 21 I'd use **virtual threads** with the simple thread-per-request model: each request gets its own virtual thread, blocking downstream calls naturally unmount from the carrier pool so a few OS threads serve millions of in-flight requests — readable synchronous code, no reactive callback hell. I'd audit for `synchronized`/native pinning, use `StructuredTaskScope` to fan out the downstream calls with deadlines and cancellation, and bound concurrency with a `Semaphore` since virtual threads themselves are cheap but downstreams aren't. In Python the equivalent is **asyncio** — single-threaded event loop, async HTTP/DB clients, `asyncio.gather`/`TaskGroup` for fan-out, semaphores for backpressure. Key contrast: Java keeps the familiar blocking API and parallelizes CPU work freely across cores; Python's loop is single-threaded and GIL-bound, so any CPU work must be pushed to a process pool to avoid stalling every coroutine.

</details>

<details>
<summary><strong>Q:</strong> How do you reason about packaging and dependency management differences that bite at runtime in Java vs Python?</summary>

Java resolves dependencies at build time (Maven/Gradle) into a classpath/module-path, and the JVM loads classes lazily by classloader — the runtime hazards are **version conflicts on a flattened classpath** (two libs needing different versions of a transitive dep, "JAR hell") and `NoSuchMethodError`/`LinkageError` surfacing only when that code path executes. Python resolves at install time into an environment; the runtime hazards are environment drift (system vs venv), the import system picking up the wrong package, and native-extension/ABI mismatches. The senior discipline is the same in spirit: pin and lock (lockfiles, dependency convergence), isolate environments (venv/containers, shaded/relocated jars), and reproduce the *exact* runtime in CI — because both ecosystems happily build green and then fail on a cold code path in prod.

</details>

<details>
<summary><strong>Q:</strong> You upgraded a performance-testing stack to Java 21 and a new testing framework. What did the runtime/GC and Loom story let you change, and what did you watch for?</summary>

Moving the perf stack to Java 21 unlocked virtual threads and the modern collectors, so a load generator could model thousands of concurrent client connections with plain blocking code on virtual threads instead of a tuned thread pool or a reactive client — far simpler to write and to scale the simulated concurrency. On the GC side I'd pick the collector to match the measurement goal: ZGC when the harness itself must not introduce pause-driven latency noise into results, G1 for throughput-oriented runs. The things I watched for: pinning from `synchronized`/native code silently capping concurrency, JIT warmup skewing early samples (warm up before measuring), and ensuring the harness's own allocation didn't add GC noise that contaminated the system-under-test's numbers.

</details>

<details>
<summary><strong>Q:</strong> You cut a Pega install from 11h to 30min and automated cert rotation with Python/Shell. Frame that as concurrency/perf engineering, not just scripting.</summary>

The 22x speedup is fundamentally about turning a long serial pipeline into a concurrent one: install/health-check steps that are I/O-bound (downloads, DB ops, remote calls, waits) parallelize cleanly, which in Python means `asyncio`/thread pools or orchestrating parallel shell stages rather than running everything sequentially. Because the work is I/O-bound, the GIL is irrelevant and threads/async are the right tools — I'd only reach for processes if a step were genuinely CPU-bound. For cert rotation and health checks I'd lean on context managers for deterministic cleanup of connections/handles, idempotent retries with backoff for flaky remote steps, and structured concurrency so one failed branch cancels the rest with a clear error — the same correctness discipline as a backend service, applied to automation.

</details>

## Say it with your resume

- **Java 21 perf-testing migration → Loom + GC fluency.** "When I upgraded our perf-testing stack to Java 21, virtual threads let me model thousands of concurrent clients with simple blocking code instead of hand-tuned thread pools, and I chose the GC (G1 vs ZGC) to keep the harness from injecting pause-driven latency noise into the measurements."
- **Backend services + REST APIs → JMM/concurrency depth.** "Building backend services and REST APIs is where happens-before, executor sizing, and avoiding N+1 queries stop being trivia — they're the difference between a service that holds p99 and one that thrashes under load."
- **Redis + control planes → allocation & latency awareness.** "Working with Redis and control planes trained me to think about tail latency and allocation pressure — caching hot paths, keeping per-request object churn low so GC stays quiet."
- **Pega install 11h→30min (Python/Shell) → I/O-bound concurrency.** "That 22x came from recognizing the pipeline was I/O-bound, so the GIL was a non-issue — I parallelized the waiting steps with concurrency rather than buying more CPU."
- **Cert rotation & health-check automation → resource discipline.** "I automated cert rotation and health checks with the same correctness rigor as backend code: context managers for deterministic cleanup, idempotent retries with backoff, structured concurrency so one failed branch fails fast."

## Sources
- [Java SE 21 Documentation](https://docs.oracle.com/en/java/javase/21/)
- [Core Libraries: Virtual Threads (Oracle, JDK 21)](https://docs.oracle.com/en/java/javase/21/core/virtual-threads.html)
- [JEP 444: Virtual Threads](https://openjdk.org/jeps/444)
- [JEP 248: Make G1 the Default Garbage Collector](https://openjdk.org/jeps/248)
- [JEP 377: ZGC – A Scalable Low-Latency Garbage Collector](https://openjdk.org/jeps/377)
- [JEP 439: Generational ZGC](https://openjdk.org/jeps/439)
- [Project Loom (OpenJDK)](https://openjdk.org/projects/loom)
- [The Z Garbage Collector (OpenJDK)](https://openjdk.org/projects/zgc)
- [Java Language Spec — Memory Model (Ch. 17)](https://docs.oracle.com/javase/specs/jls/se21/html/jls-17.html)
- [Python Glossary — global interpreter lock](https://docs.python.org/3/glossary.html#term-global-interpreter-lock)
- [Python threading — performance/GIL notes](https://docs.python.org/3/library/threading.html)
- [Python asyncio — event loop & executors](https://docs.python.org/3/library/asyncio-eventloop.html)
- [Python asyncio — to_thread](https://docs.python.org/3/library/asyncio-task.html)
- [Python gc — garbage collector interface](https://docs.python.org/3/library/gc.html)
