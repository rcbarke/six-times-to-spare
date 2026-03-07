# Six Times to Spare: GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications

This repository contains the **reproducible microbenchmark, sweep harnesses, telemetry logs, and plotting utilities** used in the paper:

**“Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications.”** 

The study evaluates **5G NR LDPC decoding performance on compact heterogeneous edge hardware**, focusing on how GPU offload changes the **compute headroom available to roadside units (RSUs) and edge gNBs supporting URLLC vehicular workloads**.

The benchmark is built on the **Sionna LDPC5G implementation** and isolates the **LDPC decode kernel** while logging system telemetry to understand **compute, utilization, and power behavior under load**.

---

# Key Results

### Dense-regime edge performance (DGX Spark)

In the **edge-relevant dense regime**

```
N_cw ∈ {2048 … 20480}
```

the **GB10 GPU on DGX Spark sustains ~5.8× throughput advantage over the Grace CPU**.

Typical dense-regime service times:

| Iterations | Grace CPU t_cb | GB10 GPU t_cb |
| ---------- | -------------- | ------------- |
| 4          | 0.153 ms       | 0.026 ms      |
| 10         | 0.373 ms       | 0.064 ms      |
| 20         | 0.725 ms       | 0.126 ms      |

Against a **0.5 ms URLLC slot budget**:

* GPU decoding uses **5–25% of the slot**
* CPU decoding can exceed **100% of the slot**

This produces the **“Six Times to Spare” edge headroom result**.

---

### Workstation comparison (COTS)

A COTS reference system (i9-14900K + RTX 4090) provides an **upper-bound comparison**, not an edge deployment recommendation.

Dense-regime results:

* **Mean speedup:** ~14.5×
* **Absolute throughput:** significantly higher
* **Power increase:** ~80–160 W above baseline during active decode windows

This comparison illustrates **raw acceleration potential**, but the **DGX Spark result is the deployment-relevant edge outcome**.

---

### Scaling regimes

The full sweep

```
N_cw = 1 … 20480
```

reveals three operating regions:

1. **Launch-limited small batches**

   * CPUs competitive
2. **GPU ramp-up**

   * parallel efficiency increases with batch size
3. **Dense steady state**

   * accelerator throughput stabilizes

This structure explains **where GPU acceleration emerges and where it disappears**.

---

# Repository Structure

```
six-times-to-spare/

├── README.md
├── plot_paper.py
│
├── install-sionna-spark/
│   ├── README.md
│   ├── check_sionna.py
│   ├── check_tensorflow.py
│   ├── inspect_tensorflow.py
│   ├── check_matplotlib_3d.py
│   └── sionna_e2e_ldpc_awgn.py
│
├── utils/
│   ├── README.md
│   ├── ldpc_sweep_seed_checkpoint.py
│   ├── ldpc_sweep_aggregate_datasets.py
│   └── recovery_watchdog.sh
│
├── dgx-spark/
│   │
│   ├── README.md
│   ├── sweep_ldpc.sh
│   ├── ldpc_cpu_gpu_benchmark.py
│   ├── plot_ldpc_results.py
│   ├── gpu_ldpc_sweep_stats.csv
│   ├── pid_ldpc_sweep_stats.log
│   ├── ldpc_sionna_spark.csv
│   ├── ldpc_sionna_spark.checkpoint
│   │
│   ├── dense-codeword/
│   │   ├── README.md
│   │   ├── sweep_ldpc.sh
│   │   ├── fig_ldpc_throughput_vs_codewords.png
│   │   ├── fig_ldpc_throughput_vs_iter.png
│   │   └── fig_ldpc_resource_utilization.png
│   │
│   └── baseline/
│       ├── README.md
│       ├── sweep_ldpc_baseline.sh
│       ├── fig_ldpc_throughput_vs_codewords.png
│       ├── fig_ldpc_throughput_vs_iter.png
│       └── fig_ldpc_resource_utilization.png
│
└── i9-14900K-rtx-4090/
    │
    ├── README.md
    ├── sweep_ldpc_cumulative.sh
    ├── ldpc_cpu_gpu_benchmark.py
    ├── plot_ldpc_results.py
    ├── gpu_ldpc_sweep_stats.csv
    ├── pid_ldpc_sweep_stats.log
    ├── ldpc_sionna_cots.csv
    ├── ldpc_sionna_cots.checkpoint
    │
    └── ldpc_spike/
        ├── README.md
        ├── profile_ldpc_spike_cots.sh
        └── focused spike ablation artifacts
```

---

# Experiments

The repository contains **two hardware studies**.

### 1️⃣ DGX Spark edge platform

```
dgx-spark/
```

Hardware:

* **Grace ARM CPU (20 cores)**
* **GB10 Blackwell GPU**
* **128 GB unified memory**
* **NVLink-C2C coherent CPU–GPU interconnect**

Experiments include:

* **baseline sweep** (small batch regime)
* **dense sweep** (edge deployment regime)
* telemetry-backed utilization analysis

---

### 2️⃣ COTS workstation comparison

```
i9-14900K-rtx-4090/
```

Hardware:

* Intel **i9-14900K CPU**
* NVIDIA **RTX 4090 GPU**
* discrete CPU/GPU memory connected via PCIe

Includes:

* full sweep replication
* **focused spike ablation**
* power-draw characterization

The spike study explains the **temporary RTX 4090 peak near N_cw ≈ 1024**.

---

# Benchmark Model

The LDPC workload implements an **NR-like link-level PHY chain**:

```
information bits
→ LDPC encoder (k=512, n=1024)
→ 16-QAM mapper
→ AWGN channel
→ soft demapper
→ LDPC decoder
```

The decoder is executed on:

```
/CPU:0
/GPU:0
```

using the **same TensorFlow/Sionna graph**, isolating hardware execution as the primary variable.

---

# Running the Experiments

### Dense sweep (edge regime)

```
cd dgx-spark
bash sweep_ldpc.sh
```

### Baseline sweep

```
cd dgx-spark/baseline
bash sweep_ldpc_baseline.sh
```

### COTS comparison

```
cd i9-14900K-rtx-4090
bash sweep_ldpc_cumulative.sh
```

### Spike ablation

```
cd i9-14900K-rtx-4090/ldpc_spike
./profile_ldpc_spike_cots.sh
```

---

# Generated Figures

Major plots used in the paper include:

* throughput vs iterations
* throughput vs codewords
* resource utilization histograms
* combined DGX vs COTS comparisons

Generated using:

```
plot_ldpc_results.py
plot_paper.py
```

---

# Telemetry

The benchmark logs both **timing and system metrics**.

GPU telemetry:

```
nvidia-smi --query-gpu=timestamp,utilization.gpu,power.draw --format=csv -l 1
```

CPU telemetry:

```
pidstat -u -p ALL 1
```

These logs support the **telemetry-backed analysis presented in the paper**, including CPU core usage, GPU occupancy, and power behavior.

---

# Citation

If you use this repository, please cite:

```
Ryan Barker, Julia Boone, Tolunay Seyfi,
Alireza Ebrahimi Dorcheh, Fatemeh Afghah,
Joseph Boccuzzi

Six Times to Spare: Characterizing GPU-Accelerated
5G LDPC Decoding for Edge-RSU Communications
```
