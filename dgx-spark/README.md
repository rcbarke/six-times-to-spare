# DGX Spark LDPC Study

This directory contains the **complete DGX Spark LDPC5G benchmark dataset** used in the paper:

**“Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications.”**

The DGX Spark experiments represent the **primary edge-platform evaluation** in the study.

Hardware platform:

| Component | Hardware |
|---|---|
| CPU | NVIDIA **Grace ARM (20 cores)** |
| GPU | NVIDIA **GB10 Blackwell GPU** |
| Memory | **128 GB coherent LPDDR5x shared memory** |
| Interconnect | **NVLink-C2C coherent CPU–GPU fabric** |

Unlike the COTS workstation experiment, this system uses a **coherent CPU–GPU memory architecture**, which eliminates PCIe host/device memory transfers and better reflects a **compact edge-compute deployment target**.

---

# Purpose

This directory contains the **full DGX Spark LDPC sweep**, covering the entire experimental range:

```

N_cw = 1 … 20480
I    = 4 … 22

```

The experiment characterizes:

- GPU acceleration of **5G LDPC decoding**
- throughput scaling with **codeword batch size**
- throughput scaling with **belief-propagation iterations**
- **CPU relief** when decoding runs on GPU
- **accelerator utilization and power behavior**

These measurements support the paper’s central finding:

> GPU offload converts LDPC decoding from a CPU-heavy bottleneck into a bounded accelerator workload, yielding roughly **6× throughput improvement** in dense edge-RSU operating regimes.

---

# Directory Structure

The DGX Spark experiments are organized into two regimes:

```

dgx-spark/
├── baseline/
├── dense-codeword/
├── sweep_ldpc_cumulative.sh
├── ldpc_sionna_spark.csv
├── gpu_ldpc_sweep_stats.csv
├── pid_ldpc_sweep_stats.log
└── plot_ldpc_results.py

```

### baseline/

Small-batch **launch-limited regime**.

```

N_cw ∈ {1,2,4,…,1024}

```

Captures the region where:

- GPU kernel launch overhead dominates
- CPU and GPU performance are closest
- GPU ramp-up behavior begins.

---

### dense-codeword/

Steady-state **edge deployment regime**.

```

N_cw ∈ {2048,…,20480}

```

Captures the region where:

- GPU occupancy saturates
- throughput stabilizes
- the paper’s **“Six Times to Spare”** result is measured.

---

# Sweep Driver

The entire DGX Spark sweep is orchestrated by:

```

sweep_ldpc_cumulative.sh

```

The script executes the LDPC benchmark across all `(N_cw , I)` pairs while:

- recording results to CSV
- logging GPU telemetry
- logging CPU utilization
- checkpointing progress for crash-safe resume

See implementation:

---

# Benchmark Driver

The benchmark itself is implemented in:

```

ldpc_cpu_gpu_benchmark.py

```

The script constructs a complete Sionna PHY chain:

```

Binary source
→ LDPC5G encoder
→ 16-QAM mapper
→ AWGN channel
→ soft demapper
→ LDPC5G decoder

```

Only the **LDPC decoder stage is timed**.

The same TensorFlow graph is executed on:

```

/CPU:0  (Grace ARM)
/GPU:0  (GB10)

```

enabling direct CPU vs GPU comparisons.

---

# Generated Data

The sweep produces the following artifacts:

| File | Description |
|---|---|
| `ldpc_sionna_spark.csv` | main results table |
| `ldpc_sionna_spark.checkpoint` | sweep checkpoint |
| `gpu_ldpc_sweep_stats.csv` | GPU telemetry |
| `pid_ldpc_sweep_stats.log` | CPU utilization log |

These files contain all data required to reproduce the paper’s plots.

---

# Post-Processing

Figures are generated using:

```

plot_ldpc_results.py

```

which produces:

```

fig_ldpc_throughput_vs_codewords.png
fig_ldpc_throughput_vs_iter.png
fig_ldpc_resource_utilization.png

```

The script parses:

- the benchmark CSV
- GPU telemetry
- pidstat CPU logs

to compute throughput and utilization statistics.

---

# Observed Behavior

Key observations from the DGX Spark sweep:

### GPU scaling

GPU throughput increases rapidly with batch size until approximately:

```

N_cw ≈ 256

```

after which the GPU reaches **steady-state throughput**.

---

### Dense-regime speedup

Across the dense regime:

```

N_cw ≥ 2048

```

the GPU maintains approximately:

```

5.7× – 5.9× throughput improvement

```

over the Grace CPU.

---

### CPU utilization

CPU decoding uses roughly:

```

~10–13 Grace cores

```

during dense runs.

GPU offload therefore frees significant CPU capacity for:

- scheduling logic
- control-plane processing
- colocated edge workloads.

---

### GPU utilization

During active decode periods:

```

GB10 utilization frequently exceeds 90%

```

indicating the dense regime successfully drives the accelerator into a **high-occupancy steady state**.

---

# Why DGX Scaling Is Smooth

The DGX Spark platform uses:

```

NVLink-C2C coherent CPU–GPU memory

```

which eliminates:

- PCIe host/device transfers
- duplicated host/GPU memory buffers
- certain runtime placement overheads.

As a result, throughput transitions smoothly from the ramp-up regime into the steady-state dense regime without the local maxima observed on discrete GPU systems.

---

# Relationship to Other Experiments

The repository contains three main experiment sets:

| Directory | Purpose |
|---|---|
| `dgx-spark/` | Edge platform evaluation |
| `i9-14900K-rtx-4090/` | COTS workstation comparison |
| `i9-14900K-rtx-4090/ldpc_spike/` | focused spike investigation |

The DGX Spark experiments represent the **edge deployment target** used to justify the paper’s architectural conclusions.

---

# Paper Reference

This dataset corresponds to:

```

Section V – Results and Evaluation
Figure 2 – Throughput scaling
Figure 3 – Resource utilization
Table I – Slot-budget interpretation

```

in the paper.

---

# Reproducibility

All scripts, logs, and plots required to reproduce the DGX Spark results are contained in this directory.

