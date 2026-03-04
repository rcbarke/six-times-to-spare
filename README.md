# Six Times to Spare — LDPC5G decoding on NVIDIA DGX Spark (Grace CPU vs GB10 GPU)

This repository contains a reproducible LDPC5G decoding microbenchmark and artifact pipeline used in the **large codeword ablation study** (dense / “urban morphology” proxy), plus a **baseline lower-bound sweep** (rural / tail-focused) and an **automated dataset consolidator** that merges both regimes into one end-to-end dataset.

At a high level:

- **Top-level sweep (dense / urban proxy):** large N<sub>cw</sub> sweep to stress batch parallelism and expose the upper throughput envelope.
- **`baseline/` sweep (rural / tail proxy):** lower-bound N<sub>cw</sub> ∈ {1, 2, 4, …, 1024} sweep designed for loose p95 tail interpretation.
- **`consolidated/` dataset:** auto-generated merge of baseline + dense artifacts spanning the full tested N<sub>cw</sub> range.

---

## Headline results (large codeword ablation)

The top-level dense sweep demonstrates a consistent **~5.7×–5.9× throughput separation** between **Grace CPU** and **GB10 GPU** across the studied operating points.

Key plots (generated artifacts):

- `fig_ldpc_throughput_vs_iter.png` — throughput degrades with more LDPC iterations for both CPU and GPU, with the GPU sustaining a ~6× lead.
- `fig_ldpc_throughput_vs_codewords.png` — throughput vs. N<sub>cw</sub> in the dense regime, showing a stable ~6× gap.
- `fig_ldpc_resource_utilization.png` — resource usage histograms during the sweep:
  - CPU usage clusters around a high-but-stable core-equivalent band during active decoding.
  - GPU utilization shows strong saturation during active samples, as expected for the dense regime.

---

## Repository layout

### File tree

```text
.
├── DGX_SPARK.md
├── README.md
├── sweep_ldpc.sh
├── ldpc_cpu_gpu_benchmark.py
├── plot_ldpc_results.py
├── ldpc_sionna_spark.csv
├── gpu_ldpc_sweep_stats.csv
├── pid_ldpc_sweep_stats.log
├── ldpc_sionna_spark.checkpoint
├── fig_ldpc_resource_utilization.png
├── fig_ldpc_throughput_vs_codewords.png
├── fig_ldpc_throughput_vs_iter.png
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
│   └── ldpc_sweep_aggregate_datasets.py
│
├── baseline/
│   ├── README.md
│   ├── sweep_ldpc_baseline.sh
│   ├── fig_ldpc_resource_utilization.png
│   ├── fig_ldpc_throughput_vs_codewords.png
│   ├── fig_ldpc_throughput_vs_iter.png
│   ├── pid_ldpc_sweep_stats.log
│   ├── ldpc_sionna_spark.checkpoint
│   ├── ldpc_sionna_spark.csv
│   └── gpu_ldpc_sweep_stats.csv
│
└── consolidated/
    ├── README.md
    ├── fig_ldpc_resource_utilization.png
    ├── fig_ldpc_throughput_vs_codewords.png
    ├── fig_ldpc_throughput_vs_iter.png
    ├── pid_ldpc_sweep_stats.log
    ├── ldpc_sionna_spark.checkpoint
    ├── ldpc_sionna_spark.csv
    └── gpu_ldpc_sweep_stats.csv
```

> Notes:
>
> * `baseline/` and `consolidated/` mirror the **same artifact naming convention** as the top-level dense sweep so downstream plotting and analysis can treat them uniformly.
> * `consolidated/` is **generated** by `utils/ldpc_sweep_aggregate_datasets.py`. It can be deleted and regenerated at any time.

---

## Platform documentation (DGX_SPARK.md)

* NVIDIA DGX Spark is a compact, 240 W Grace–Blackwell (GB10) desktop AI system with a 20-core Arm Grace CPU, Blackwell GPU (5th-gen Tensor Cores, FP4), and 128 GB coherent unified LPDDR5x memory over NVLink-C2C. 
* It includes 4 TB self-encrypting NVMe storage plus high-speed I/O (ConnectX-7 200 Gbps, 10 GbE, Wi-Fi 7, USB-C, HDMI) and is positioned for local prototyping, fine-tuning, and multi-model/agentic inference, with stated single-node capacity up to ~200B parameters (FP4) and ~405B across two linked units. 
* The document also clarifies power reporting (e.g., `nvidia-smi` reflects GPU power, not total draw) and provides a DGX OS recovery/reflash guide plus a high-level comparison against GH200/GB200 rack-scale systems. 

---

## Subdirectory structure

### `install-sionna-spark/`

DGX Spark bring-up and validation utilities: install notes, environment checks, and a known-good end-to-end Sionna LDPC example to confirm functional correctness and device visibility (TensorFlow/Sionna/GPU).

### `utils/`

Repository organization for dataset-manipulation utilities (originally designed to run from the same directory as the sweep harness at repo root):

* `ldpc_sweep_seed_checkpoint.py`
  Seeds/repairs checkpoint state from existing artifacts to support deterministic resumption.
* `ldpc_sweep_aggregate_datasets.py`
  Merges baseline (`baseline/`) + dense (repo root) artifacts into `consolidated/`.

### `baseline/`

Lower-bound, tail-focused sweep:

* N<sub>cw</sub> ∈ {1, 2, 4, …, 1024} (powers of two)
* Rural morphology proxy + loose p95 tail studies

Contains its own sweep driver (`sweep_ldpc_baseline.sh`) and a full artifact set (CSVs/logs/checkpoint/figures).

### `consolidated/`

Auto-generated merge of baseline + dense datasets, intended as the **single source of truth** for end-to-end plotting and reporting across the full tested N<sub>cw</sub> range.

---

## Top-level (dense) sweep harness and artifacts

### Sweep driver

* `sweep_ldpc.sh`
  Runs the dense/urban-proxy sweep and produces the top-level artifacts listed below.

### Core artifacts produced by the dense sweep

* `ldpc_sionna_spark.csv` — primary results table (per-ablation measurements)
* `gpu_ldpc_sweep_stats.csv` — GPU / sweep telemetry statistics
* `pid_ldpc_sweep_stats.log` — pidstat-style process/system utilization log
* `ldpc_sionna_spark.checkpoint` — resume state for interrupted sweeps

### Figures (generated)

* `fig_ldpc_throughput_vs_iter.png`
* `fig_ldpc_throughput_vs_codewords.png`
* `fig_ldpc_resource_utilization.png`

### Analysis / plotting

* `plot_ldpc_results.py`
  Post-processes sweep artifacts and generates the figures.

### Benchmark entrypoint

* `ldpc_cpu_gpu_benchmark.py`
  Main benchmark logic used by the sweep harness (CPU vs GPU decode path, iteration sweep, codeword sweep).

---

## Running the experiments

### 1) Dense (large codeword) ablation

From the repository root:

```bash
bash sweep_ldpc.sh
```

### 2) Baseline (tail-focused) ablation

From the repository root:

```bash
cd baseline
bash sweep_ldpc_baseline.sh
```

### 3) Consolidate datasets (baseline + dense)

From the repository root:

```bash
python3 utils/ldpc_sweep_aggregate_datasets.py
```

This writes merged artifacts into `consolidated/`.

---

## Recommended workflow

1. Run the **dense sweep** (repo root) to capture saturation behavior in large `\($N_{cw}$)` regimes.
2. Run the **baseline sweep** (`baseline/`) for lower-bound behavior and tail interpretation.
3. Run the **aggregator** to produce a single dataset in `consolidated/`.
4. Use `plot_ldpc_results.py` (or your downstream analysis pipeline) against `consolidated/` for end-to-end figures that span both regimes.

---

## Reproducibility notes

* Treat `baseline/` and `consolidated/` as artifact directories; delete/regenerate as needed.
* Checkpoints are intended to support resumption and should not be manually edited unless you know exactly what you’re doing.
* If you refactor schema (CSV column names, telemetry formats), regenerate consolidated artifacts to keep downstream plotting consistent.

---

## Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications

This repository contains the **reproducible, telemetry-backed microbenchmark** and plotting utilities used in the paper:

**“Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications.”** 

The goal is simple: **isolate and measure LDPC5G decoding headroom** on a compact heterogeneous edge node (DGX Spark), comparing **Grace CPU** vs **GB10 GPU** under a deliberately heavy stress sweep over:
- batch parallelism (**$N_{cw}$ = 2048 → 20480**) and
- belief-propagation iterations (**$I$ = 4 → 22**),
timing **only the decode kernel** while logging CPU/GPU utilization and power. 

---

### What this study shows

Across the full sweep, GPU offload provides a stable, repeatable throughput advantage:
- **Mean GPU/CPU throughput speedup ≈ 5.8×** (median ≈ 5.8×; min ≈ 4.7×; max ≈ 6.4×). 
- Throughput declines with iterations (expected), but the **speedup holds across $I$**. 

#### URLLC slot-headroom interpretation (0.5 ms slot)
Using amortized per-codeword service time \($t_{cb} = t_{dec}/N_{cw}$\) and normalizing by **$T_{slot}$ = 0.5 ms**:
- **CPU** reaches **0.720 ms at I=20** (i.e., **1.44× the slot**).
- **GPU** reaches **0.125 ms at I=20** (i.e., **0.25× the slot**). 

#### Telemetry-backed resource shift
During active decode periods:
- CPU-based decoding consumes on the order of **~10 “core-equivalents”**.
- GPU-based decoding drives **high accelerator utilization (often ~90%+)**.
- Incremental GPU power during active decode is **~10–15 W above low-utilization baseline**, trading ~10 CPU cores for modest accelerator power. 

---

### Key top-level artifacts

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

### System model and workload (what we benchmark)

We implement an NR-like link-level chain using Sionna LDPC5G components:
- ($k$, $n$) = (512, 1024), rate $R$ = 1/2
- 16-QAM mapping
- AWGN channel
- soft demapper generates LLRs
- LDPC decoder consumes an LLR tensor of shape \($N_{cw} \times n$\) 

**Important:** the benchmark is designed to **stress and saturate** the compute substrate to expose an **upper envelope** of throughput/headroom; it is not trying to emulate a specific scheduler instance. The paper focuses on the larger $N_{cw}$ ablations within the top-level repository, the smaller batch `baseline/` results are included for completeness but not the primary focus.

---

### Reproducing the paper figures

#### 1) Run the sweep
```bash
bash sweep_ldpc.sh
```

This produces (or appends to):

* `ldpc_sionna_spark.csv`

#### 2) Additional telemetry

The sweep script will log raw LDPC timing statistics as well as the following system-level resource utilization metrics:

**GPU telemetry:**

```bash
nvidia-smi --query-gpu=timestamp,utilization.gpu,power.draw --format=csv -l 1 > gpu_ldpc_sweep_stats.csv
```

**CPU telemetry (benchmark process):**

```bash
pidstat -u -p ALL 1 > pid_ldpc_sweep_stats.log
```

#### 3) Plot

```bash
python3 plot_ldpc_results.py
```

Outputs:

* `fig_ldpc_throughput_vs_iter.png (Figure 1)` 
* `fig_ldpc_throughput_vs_codewords.png (described in text)`
* `fig_ldpc_resource_utilization.png (Figure 2)`

---

### Metrics reported

Per configuration ($N_{cw}$, $I$), the harness reports:

* batch decode latency: ($t_{dec}$)
* throughput: ($T_{thr} = \frac{N_{cw} \cdot k}{t_{dec}}$)
* amortized per-codeword service time: ($t_{cb} = \frac{t_{dec}}{N_{cw}}$)

Timing includes explicit synchronization so asynchronous GPU work completes before stopping the timer.

---

### Scope

This repo supports a **compute characterization** of the LDPC kernel:

* ($t_{cb}$) is **amortized under batch-parallel execution**, not “arrival-at-idle” single-codeword latency.
* The workload uses AWGN and reuses a fixed LLR tensor for timing consistency.
* Stronger URLLC latency claims would require **small-batch and tail-latency (p95/p99/p99.99)** measurements in a more integrated real-time stack.

---

### Citation

If you use this repository, please cite the paper draft:

> Ryan Barker, Julia Boone, Tolunay Seyfi, Alireza Ebrahimi Dorcheh, Fatemeh Afghah, Joseph Boccuzzi,
> “Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications.”

```bibtex
@unpublished{barker_six_times_to_spare,
  title   = {Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications},
  author  = {Barker, Ryan and Boone, Julia and Seyfi, Tolunay and Ebrahimi Dorcheh, Alireza, Afghah, Fatemeh, and Boccuzzi, Joseph},
  note    = {Paper draft},
  year    = {2026}
}
```
