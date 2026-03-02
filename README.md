# Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications

This repository contains the **reproducible, telemetry-backed microbenchmark** and plotting utilities used in the paper:

**“Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications.”** 

The goal is simple: **isolate and measure LDPC5G decoding headroom** on a compact heterogeneous edge node (DGX Spark), comparing **Grace CPU** vs **GB10 GPU** under a deliberately heavy stress sweep over:
- batch parallelism (**$N_{cw}$ = 4096 → 20480**) and
- belief-propagation iterations (**$I$ = 4 → 22**),
timing **only the decode kernel** while logging CPU/GPU utilization and power. 

---

## What this study shows

Across the full sweep, GPU offload provides a stable, repeatable throughput advantage:
- **Mean GPU/CPU throughput speedup ≈ 5.8×** (median ≈ 5.8×; min ≈ 4.7×; max ≈ 6.4×). 
- Throughput declines with iterations (expected), but the **speedup holds across $I$**. 

### URLLC slot-headroom interpretation (0.5 ms slot)
Using amortized per-codeword service time \($t_{cb} = t_{dec}/N_{cw}$\) and normalizing by **$T_{slot}$ = 0.5 ms**:
- **CPU** reaches **0.720 ms at I=20** (i.e., **1.44× the slot**).
- **GPU** reaches **0.125 ms at I=20** (i.e., **0.25× the slot**). 

### Telemetry-backed resource shift
During active decode periods:
- CPU-based decoding consumes on the order of **~10 “core-equivalents”**.
- GPU-based decoding drives **high accelerator utilization (often ~90%+)**.
- Incremental GPU power during active decode is **~10–15 W above low-utilization baseline**, trading ~10 CPU cores for modest accelerator power. 

---

## Repository layout

**Benchmark**
- `ldpc_cpu_gpu_benchmark.py` — generates LLRs once, then times **only LDPC5G decode** on `/CPU:0` and `/GPU:0`; appends run summaries to CSV.

**Sweep + checkpointing**
- `sweep_ldpc.sh` — runs the ($N_{cw}$, $I$) sweep and logs results
- `ldpc_sweep_seed_checkpoint.py` — derives a resume checkpoint from the results CSV

**Telemetry + plotting**
- `gpu_ldpc_sweep_stats.csv` — `nvidia-smi` sampled utilization/power
- `pid_ldpc_sweep_stats.log` — process CPU accounting (e.g., pidstat)
- `plot_ldpc_results.py` — regenerates:
  - `fig_ldpc_throughput_vs_iter.png`
  - `fig_ldpc_resource_utilization.png`

---

## System model and workload (what we benchmark)

We implement an NR-like link-level chain using Sionna LDPC5G components:
- ($k$, $n$) = (512, 1024), rate $R$ = 1/2
- 16-QAM mapping
- AWGN channel
- soft demapper generates LLRs
- LDPC decoder consumes an LLR tensor of shape \($N_{cw} \times n$\) 

**Important:** the benchmark is designed to **stress and saturate** the compute substrate to expose an **upper envelope** of throughput/headroom; it is not trying to emulate a specific scheduler instance. 

---

## Reproducing the paper figures

### 1) Run the sweep
```bash
bash sweep_ldpc.sh
````

This produces (or appends to):

* `ldpc_sionna_spark.csv`

### 2) Collect telemetry (recommended)

Run these in parallel with the sweep.

**GPU telemetry:**

```bash
nvidia-smi --query-gpu=timestamp,utilization.gpu,power.draw --format=csv -l 1 > gpu_ldpc_sweep_stats.csv
```

**CPU telemetry (benchmark process):**

```bash
pidstat -u -p ALL 1 > pid_ldpc_sweep_stats.log
```

### 3) Plot

```bash
python3 plot_ldpc_results.py
```

Outputs:

* `fig_ldpc_throughput_vs_iter.png`
* `fig_ldpc_resource_utilization.png`

---

## Metrics reported (paper-consistent)

Per configuration ($N_{cw}$, $I$), the harness reports:

* batch decode latency: ($t_{dec}$)
* throughput: ($T_{thr} = \frac{N_{cw} \cdot k}{t_{dec}}$)
* amortized per-codeword service time: ($t_{cb} = \frac{t_{dec}}{N_{cw}}$) 

Timing includes explicit synchronization so asynchronous GPU work completes before stopping the timer. 

---

## Scope

This repo supports a **compute characterization** of the LDPC kernel:

* ($t_{cb}$) is **amortized under batch-parallel execution**, not “arrival-at-idle” single-codeword latency.
* The workload uses AWGN and reuses a fixed LLR tensor for timing consistency.
* Stronger URLLC latency claims would require **small-batch and tail-latency (p95/p99/p99.99)** measurements in a more integrated real-time stack. 

---

## Citation

If you use this repository, please cite the paper draft:

> Ryan Barker, Julia Boone, Tolunay Seyfi, Alireza Ebrahimi Dorcheh, Fatemeh Afghah,
> “Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications.”
