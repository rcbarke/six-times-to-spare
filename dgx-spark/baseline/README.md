# baseline/ — LDPC baseline sweep (rural / tail-focused)

This subdirectory contains the **baseline (lower-bound) LDPC sweep** and its generated artifacts. The baseline sweep covers a smaller, power-of-two codeword range:

- **Codewords:** `N_cw ∈ {1, 2, 4, …, 1024}`
- **Purpose:** characterize **rural morphologies** and loosely characterize **p95 tail behavior** (latency/throughput/resource utilization under lighter batching). This dataset can't make p99 claims since it is measured offline, does not fully model RAN timing, and each data point is a stored average across ten runs. We'd need per-batch sampling fully online to measure p99.

The baseline artifacts intentionally share the **same naming convention** as the top-level (dense/urban) sweep outputs so they can be combined later into a single unified dataset.

---

## Files

### Sweep harness
- `sweep_ldpc_baseline.sh`  
  Baseline sweep driver script (lower-bound `N_cw` range). Produces the dataset artifacts listed below.

### Generated dataset artifacts
These files are produced by the baseline sweep and represent the complete baseline run:

- `ldpc_sionna_spark.csv`  
  Primary results table for the baseline sweep (per-ablation measurements).

- `gpu_ldpc_sweep_stats.csv`  
  GPU-focused telemetry/statistics captured during the sweep (as emitted by the measurement harness).

- `ldpc_sionna_spark.checkpoint`  
  Checkpoint file used to resume an interrupted sweep. Stores the last completed sweep state.

- `pid_ldpc_sweep_stats.log`  
  System/process resource utilization log captured during the sweep (pidstat-style).

### Generated figures
These plots are rendered from the baseline results and correspond to the same figure naming used at the repository root:

- `fig_ldpc_throughput_vs_iter.png`  
  Throughput as a function of LDPC iterations (iteration sensitivity).

- `fig_ldpc_throughput_vs_codewords.png`  
  Throughput as a function of codeword batch size `N_cw` (baseline lower-bound sweep).

- `fig_ldpc_resource_utilization.png`  
  Resource utilization summary (CPU/GPU/system metrics), derived from sweep telemetry.

---

## How to run the baseline sweep

From the repository root, run:

```bash
cd baseline/
bash sweep_ldpc_baseline.sh
```

This test is intended to be run in an independent subdirectory from the `sweep_ldpc.sh` large codeword ablation. It will generate the CSV artifacts, logs, checkpoint, and figures in **this `baseline/` directory, with identical naming convention**.

> Tip: If a sweep is interrupted, the script should resume from `ldpc_sionna_spark.checkpoint` (if present). If you need to reconstruct checkpoint state from existing artifacts, use the checkpoint seeding utility in `utils/`.

---

## How to use these baseline artifacts

### 1) Tail-focused analysis (standalone)

Use the CSV/logs/figures here directly to study:

* low-batch behavior (`N_cw` small),
* performance variability (tail latency / tail throughput behavior),
* resource utilization under lighter batching.

### 2) Consolidation with the dense (urban) sweep

The baseline and dense sweeps are designed to be **merge-compatible**. To combine baseline (`N_cw ≤ 1024`) with the top-level dense sweep (extending up to the maximum `N_cw` tested), run the dataset aggregation utility (from repo root):

```bash
python3 utils/ldpc_sweep_aggregate_datasets.py
```

This writes merged artifacts to:

* `consolidated/`

---

## Intent

* **Baseline sweep (`baseline/`)**: lower-bound batching, rural morphology proxy, tail studies (p95 emphasis).
* **Top-level sweep (repo root)**: dense batching, urban morphology proxy, saturation/upper-envelope behavior.
* **Consolidated dataset (`consolidated/`)**: unified view across the full `N_cw` range for end-to-end plots and reporting.
