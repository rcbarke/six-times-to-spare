# COTS LDPC5G Benchmark (i9-14900K + RTX 4090)

This directory contains the **complete LDPC5G scaling study performed on a COTS workstation** used in the paper:

**“Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications.”**

The platform used in this experiment:

| Component | Hardware |
|---|---|
| CPU | Intel **i9-14900K** |
| GPU | NVIDIA **RTX 4090 (AD102)** |
| System memory | DDR5 |
| GPU memory | GDDR6X |
| Interconnect | **PCIe Gen4 x16** |

This system represents a **high-performance discrete CPU/GPU workstation**. In the paper it is used as a **comparison ceiling**, not an edge deployment target.

---

# Study Purpose

This experiment evaluates **LDPC5G decoder scaling across batch size and iteration count** using the Sionna PHY stack.

The goals are to measure:

- CPU vs GPU throughput
- LDPC decode latency
- GPU acceleration scaling
- CPU relief when the decoder is offloaded
- resource utilization (CPU cores and GPU load)

The COTS study complements the **DGX Spark edge study** by showing how the same LDPC workload behaves on a traditional **discrete-memory workstation architecture**.

---

# Benchmark Overview

The full sweep evaluates:

```

N_cw = 1 … 20480
I    = 4 … 22

```

Where:

| Variable | Meaning |
|---|---|
| `N_cw` | number of codewords decoded concurrently |
| `I` | belief-propagation iterations in the LDPC5G decoder |

For each `(N_cw , I)` configuration:

```

10 decode repetitions
10 outer sweep repetitions

```

This produces **100 samples per configuration**.

---

# Benchmark Driver

The LDPC benchmark is implemented in:

```

ldpc_cpu_gpu_benchmark.py

```

It builds a complete Sionna link chain:

```

Binary source
→ LDPC5G encoder
→ 16-QAM mapper
→ AWGN channel
→ soft demapper
→ LDPC5G decoder

```

Only the **LDPC decode stage is timed**.

The script executes the same TensorFlow graph on:

```

/CPU:0
/GPU:0

```

allowing a direct CPU vs GPU comparison.

---

# Running the Full Sweep

The full COTS sweep is executed using:

```

sweep_ldpc_cumulative.sh

```

This script runs the benchmark across all `(N_cw , I)` combinations while:

- checkpointing progress
- automatically resuming after interruptions
- logging CPU and GPU telemetry

Sweep parameters:

```

N_cw ∈ {1,2,4,…,20480}
I    ∈ {4,6,8,…,22}
repetitions = 10

```

---

# Monitoring and Telemetry

During the sweep, system telemetry is recorded in parallel.

## GPU telemetry

```

gpu_ldpc_sweep_stats.csv

```

Collected via:

```

nvidia-smi --query-gpu=timestamp,utilization.gpu,power.draw

```

Metrics include:

- GPU utilization
- GPU power draw

---

## CPU telemetry

```

pid_ldpc_sweep_stats.log

```

Collected using:

```

pidstat -u -p ALL

```

From this log we estimate:

```

active CPU cores ≈ CPU% / 100

```

In the dense LDPC regime the Python process frequently consumes:

```

~27–30 active CPU cores

```

even when the decoder runs on GPU.

---

# Watchdog Supervision

Large sweeps can run for many hours.

The script:

```

recovery_watchdog.sh

```

supervises the sweep and restarts it if the benchmark crashes.

The watchdog runs the sweep inside a persistent `tmux` session and continuously checks process health.

---

# Post-Processing

Results and telemetry are processed using:

```

plot_ldpc_results.py

```

This script produces the figures used in the paper:

```

fig_ldpc_throughput_vs_codewords.png
fig_ldpc_throughput_vs_iter.png
fig_ldpc_resource_utilization.png

```

These figures show:

- GPU throughput scaling vs batch size
- iteration-dependent decode throughput
- CPU vs GPU resource utilization during the sweep

---

# Observed Behavior

The full sweep reveals three operating regions:

### 1. Launch-limited small batches

```

N_cw ≤ 8

```

GPU launch overhead dominates and CPUs remain competitive.

---

### 2. GPU ramp-up region

```

16 ≤ N_cw ≤ 512

```

GPU occupancy increases rapidly and throughput improves.

---

### 3. Dense steady-state regime

```

N_cw ≥ 2048

```

Throughput stabilizes and GPU speedup reaches approximately:

```

≈ 15×

```

relative to the i9-14900K CPU.

---

# Local Maximum Near N_cw ≈ 1024

The COTS platform exhibits a temporary throughput peak near:

```

N_cw ≈ 1024

```

This behavior is analyzed in the focused spike study located in:

```

ldpc_spike/

```

That experiment shows:

- the peak is reproducible
- PCIe saturation is **not** the cause
- the implementation uses a **hybrid CPU+GPU runtime**

The most supported explanation is a **medium-batch compute/locality sweet spot** where GPU occupancy is high while decoder workspace and runtime orchestration remain favorable.

---

# Relationship to the DGX Spark Study

The main paper result focuses on **DGX Spark**, which integrates:

```

Grace CPU + GB10 GPU

```

via coherent:

```

NVLink-C2C shared memory

```

Because Spark removes the discrete host/device boundary, the throughput curve is **much smoother** and the temporary spike observed on COTS is greatly reduced.

---

# Paper Reference

Results from this directory correspond to:

```

Figure 2 (COTS curves)
Figure 3 (resource utilization)
Section V – Results and Evaluation

```

in the paper.

---

# Reproducibility

All scripts, logs, and plots required to reproduce the COTS results are included in this directory.
