# DGX Spark Baseline LDPC Sweep (Small-Batch / Launch-Limited Regime)

This directory contains the **baseline LDPC5G sweep performed on DGX Spark** covering the **small-batch regime** of the experiment.

Platform used:

| Component | Hardware |
|---|---|
| CPU | NVIDIA **Grace ARM (20 cores)** |
| GPU | NVIDIA **GB10 Blackwell GPU** |
| Memory | **128 GB coherent LPDDR5x shared memory** |
| Interconnect | **NVLink-C2C coherent CPU–GPU fabric** |

This experiment characterizes the **launch-limited and GPU ramp-up region** of LDPC decoding performance.

---

# Purpose

The baseline sweep measures decoder performance when **batch sizes are small**, which occurs in:

- rural or lightly loaded cells
- early pipeline ramp-up
- tail-oriented latency analysis

It captures the regime where:

```text
CPU and GPU performance are closest
````

because GPU kernel launch overhead dominates.

---

# Baseline Sweep Configuration

The baseline sweep evaluates:

```text
N_cw ∈ {1, 2, 4, …, 1024}
I    ∈ {4, 6, 8, …, 22}
```

Where:

| Variable | Meaning                                  |
| -------- | ---------------------------------------- |
| `N_cw`   | number of codewords decoded concurrently |
| `I`      | belief-propagation iterations            |

Each configuration performs:

```text
10 decode repetitions
10 outer sweep repetitions
```

producing **100 samples per configuration**.

---

# Sweep Driver

The baseline sweep is executed using:

```text
sweep_ldpc_baseline.sh
```

which runs the LDPC benchmark driver:

```text
ldpc_cpu_gpu_benchmark.py
```

The benchmark constructs a full Sionna PHY chain:

```text
Binary source
→ LDPC5G encoder
→ 16-QAM mapper
→ AWGN channel
→ soft demapper
→ LDPC5G decoder
```

Only the **decoder stage is timed**.

---

# Telemetry Collection

During the sweep the system records telemetry.

## GPU telemetry

```text
gpu_ldpc_sweep_stats.csv
```

Captured using:

```text
nvidia-smi --query-gpu=timestamp,utilization.gpu,power.draw
```

Metrics include:

* GPU utilization
* GPU power draw

## CPU telemetry

```text
pid_ldpc_sweep_stats.log
```

Collected via:

```text
pidstat -u -p ALL
```

From this log we estimate:

```text
active CPU cores ≈ CPU% / 100
```

This helps quantify **CPU relief when decoding is offloaded to GPU**.

---

# Generated Results

Running the sweep produces:

| File                           | Description             |
| ------------------------------ | ----------------------- |
| `ldpc_sionna_spark.csv`        | main results table      |
| `ldpc_sionna_spark.checkpoint` | sweep resume checkpoint |
| `gpu_ldpc_sweep_stats.csv`     | GPU telemetry           |
| `pid_ldpc_sweep_stats.log`     | CPU utilization log     |

---

# Generated Figures

Figures are produced using:

```text
plot_ldpc_results.py
```

which generates:

```text
fig_ldpc_throughput_vs_iter.png
fig_ldpc_throughput_vs_codewords.png
fig_ldpc_resource_utilization.png
```

These figures summarize:

* throughput vs iteration count
* throughput vs number of codewords
* CPU/GPU resource utilization during the sweep

---

# Relationship to Other Experiments

The DGX Spark experiments are split into two regimes:

| Directory         | Purpose                           |
| ----------------- | --------------------------------- |
| `baseline/`       | small-batch launch-limited regime |
| `dense-codeword/` | steady-state edge regime          |

The **dense-codeword experiment** measures:

```text
N_cw ∈ {2048 … 20480}
```

where GPU acceleration stabilizes and the paper’s
**“Six Times to Spare”** claim is measured.

Together, these two sweeps produce the **complete DGX Spark ablation**:

```text
N_cw = 1 … 20480
```

---

# Running the Baseline Sweep

From the repository root:

```bash
cd dgx-spark/baseline
bash sweep_ldpc_baseline.sh
```

The script automatically:

* records telemetry
* checkpoints progress
* resumes interrupted sweeps

---

# Paper Reference

This dataset contributes to:

* Figure 2 (baseline region)
* Figure 3 (resource utilization)
* Section V – Results and Evaluation

in the paper.

---

# Reproducibility

All scripts, logs, and plots required to reproduce the DGX Spark baseline results are included in this directory.
