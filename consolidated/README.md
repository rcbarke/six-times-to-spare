# consolidated/ — Unified LDPC sweep dataset (baseline + dense)

This directory contains **auto-generated, consolidated artifacts** produced by the repository’s dataset aggregation utility:

- `utils/ldpc_sweep_aggregate_datasets.py`

The goal of `consolidated/` is to provide a **single, merge-compatible dataset** spanning the full tested codeword sweep range by combining:

1) **Top-level (dense) sweep artifacts**  
   - Dense/urban morphology proxy (large codeword sweep)

2) **`baseline/` sweep artifacts**  
   - Lower-bound/rural morphology proxy (loose p95 tail-focused sweep, `N_cw ∈ {1 … 1024}` in powers of two)

Once the baseline sweep completes, re-running the aggregator produces a consolidated dataset that covers the **full codeword range** end-to-end (e.g., `N_cw ∈ {1 … 20480}` depending on the dense sweep maximum).

---

## How this directory is produced

From the **repository root**, run:

```bash
python3 utils/ldpc_sweep_aggregate_datasets.py
````

The script reads artifacts from:

* repository root (dense sweep outputs), and
* `baseline/` (baseline sweep outputs),

and writes merged outputs into:

* `consolidated/`

> Treat this directory as **generated**. It can be deleted and regenerated at any time.

---

## Contents (generated artifacts)

The consolidated directory mirrors the standard artifact naming convention used by both the dense and baseline runs.

### Primary results

* `ldpc_sionna_spark.csv`
  **Consolidated results table** across both sweeps. This is the main “single source of truth” dataset for plotting and post-processing once you want the full `N_cw` range.

### Telemetry / sweep statistics

* `gpu_ldpc_sweep_stats.csv`
  Consolidated GPU-side and/or sweep telemetry statistics captured during runs (as emitted by the harness).

* `pid_ldpc_sweep_stats.log`
  Consolidated system/process utilization log (pidstat-style), formed by concatenating the source logs with light header de-duplication.

### Resume state

* `ldpc_sionna_spark.checkpoint`
  Consolidated checkpoint regenerated from the consolidated results CSV, enabling a consistent “last completed state” reference when resuming or validating sweep coverage.

---

## Merge semantics

* CSV artifacts are merged by **concatenation + row-level de-duplication**, then sorted when common sweep keys are present (e.g., `num_codewords`/`N_cw`, `num_iter`, `repeat`, timestamps).
* Logs are merged by concatenation, with light header de-duplication for pidstat-like formats.
* The consolidated checkpoint is **regenerated** based on the consolidated results CSV when possible (rather than attempting to merge checkpoint files directly).

---

## When to use `consolidated/`

Use the consolidated dataset when you want:

* a single set of plots spanning baseline + dense regimes,
* consistent, loose p95 tail interpretation across the low-`N_cw` region alongside saturation behavior at high `N_cw`,
* a clean input for any downstream plotting/reporting pipeline (rather than manually stitching datasets).

If you only care about tail behavior, work directly from `baseline/`. If you only care about saturation behavior in dense regimes, work from the top-level artifacts. For end-to-end reporting, use `consolidated/`.

