# DGX Spark Dense-Codeword LDPC Sweep

This directory contains the **dense-codeword LDPC5G benchmark performed on NVIDIA DGX Spark**.  
It corresponds to the **edge-focused portion of the experiments** reported in the paper:

**“Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications.”**

The DGX Spark platform evaluated here:

| Component | Hardware |
|---|---|
| CPU | NVIDIA **Grace ARM (20 cores)** |
| GPU | NVIDIA **GB10 Blackwell GPU** |
| Memory | **128 GB coherent LPDDR5x shared memory** |
| Interconnect | **NVLink-C2C coherent CPU–GPU fabric** |

Unlike the COTS workstation experiment, this platform represents a **compact heterogeneous edge node**, where CPU and GPU share a unified memory space rather than communicating across PCIe.

---

# Study Purpose

This directory implements the **dense-codeword regime** of the LDPC5G study.

The objective is to characterize **steady-state LDPC decoder throughput on an edge platform** once GPU occupancy has fully ramped up.

This portion of the experiment answers:

- What throughput advantage does GPU offload provide on an **edge-class node**?
- How stable is the acceleration across **LDPC iteration counts**?
- How much **CPU relief** occurs when decoding runs on GPU?

The results correspond directly to the **“Six Times to Spare”** claim in the paper.

---

# Dense Regime Configuration

This sweep evaluates:

```

N_cw ∈ {2048, 4096, … , 20480}
I    ∈ {4, 6, 8, … , 22}

```id="dense_cfg"

Where:

| Variable | Meaning |
|---|---|
| `N_cw` | number of concurrent codewords decoded |
| `I` | belief-propagation iterations |

For each `(N_cw , I)` configuration:

```

10 decode repetitions
10 outer sweep repetitions

```

This produces **100 samples per configuration**.

The dense regime intentionally avoids the GPU launch-limited region in order to measure **steady-state accelerator behavior**.

---

# Benchmark Driver

The LDPC benchmark driver is:

```

ldpc_cpu_gpu_benchmark.py

```

The script constructs a full Sionna link-level chain:

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

/CPU:0   (Grace ARM)
/GPU:0   (GB10)

```

allowing a direct CPU vs GPU comparison.  
See the driver implementation: 

---

# Running the Sweep

The dense sweep is executed using:

```

sweep_ldpc.sh

```

This script runs the benchmark across all `(N_cw , I)` pairs while:

- recording results to CSV
- logging GPU utilization
- logging CPU process activity
- checkpointing progress

Sweep parameters are defined in the script: 

---

# Monitoring and Telemetry

Two telemetry streams are collected during the sweep.

## GPU telemetry

```

gpu_ldpc_sweep_stats.csv

```

Collected using:

```

nvidia-smi --query-gpu=timestamp,utilization.gpu,power.draw

```

Metrics recorded:

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

On DGX Spark the LDPC Python process typically consumes:

```

~11–13 Grace CPU cores

```

during dense decode runs.

---

# Post-Processing

Results are processed using:

```

plot_ldpc_results.py

```

This script generates the figures used in the paper:

```

fig_ldpc_throughput_vs_codewords.png
fig_ldpc_throughput_vs_iter.png
fig_ldpc_resource_utilization.png

```

Example plots included in this directory:

- throughput vs codewords
- throughput vs iterations
- CPU/GPU resource utilization

See the plotting implementation: 

---

# Observed Behavior

In the dense regime the DGX Spark platform exhibits **stable GPU acceleration**:

```

≈ 5.7× – 5.9× GPU/CPU throughput speedup

```

across all tested iteration counts.

Key observations:

- GPU throughput stabilizes once `N_cw ≥ 2048`
- GPU speedup remains consistent across iterations
- CPU workload drops significantly when decoding is offloaded
- GPU utilization frequently approaches **90–100 %**

These results support the **“Six Times to Spare”** claim for edge-RSU LDPC decoding.

---

# Why the Curve is Smooth on DGX Spark

The dense DGX results do **not exhibit the temporary spike seen on the COTS system**.

The primary reason is architectural:

```

DGX Spark uses coherent NVLink-C2C memory

```

which allows the CPU and GPU to access the same memory pool.

This eliminates:

- PCIe transfer overhead
- host/device memory duplication
- certain runtime placement artifacts

As a result, throughput scaling on DGX Spark transitions smoothly into the steady-state regime.

---

# Relationship to Other Experiments

This repository contains three complementary experiments:

| Directory | Purpose |
|---|---|
| `dgx-spark/dense-codeword/` | Edge platform steady-state LDPC scaling |
| `i9-14900K-rtx-4090/` | COTS workstation full sweep |
| `i9-14900K-rtx-4090/ldpc_spike/` | Focused spike investigation near `N_cw ≈ 1024` |

The DGX Spark results form the **primary edge-deployment analysis** in the paper.

---

# Paper Reference

Results from this directory correspond to:

```

Figure 2 (DGX Spark curves)
Figure 3 (resource utilization)
Section V – Results and Evaluation

```

in the paper.

---

# Reproducibility

All scripts, logs, and plots required to reproduce the DGX Spark dense regime results are included in this directory.`

