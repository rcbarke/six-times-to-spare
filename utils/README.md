# utils/ — LDPC sweep dataset utilities

This directory contains small, standalone utilities used to manipulate the artifacts produced by the LDPC sweep test harness (the top-level `sweep_ldpc*.sh` scripts and their associated output files).

> **Important (execution context):** Both dataset manipulation scripts were **designed to be run from the same directory as the main LDPC sweep test harness (e.g. the repository root)**, where the sweep scripts and top-level dataset artifacts live. They have been **relocated into `utils/` strictly for repository organization**.
>
> When running them, either:
> - `cd` to the repository root first, and invoke them by path, or
> - run them from `utils/` but pass `--repo-root ..` (where supported).

---

## Contents

### `ldpc_sweep_aggregate_datasets.py`
Aggregates dataset artifacts from:
- the repository root (dense / “urban morphology” codeword sweep artifacts), and
- the `baseline/` subdirectory (lower-bound / “rural morphology” sweep artifacts, useful for p95/p99 tail studies),

into a single consolidated dataset spanning the full `N_cw` range (e.g., `{1 … 20480}`), writing merged artifacts to:
- `consolidated/` (relative to the repository root)

Typical behavior:
- Merges CSV artifacts by concatenation + de-duplication (and sorting where possible).
- Concatenates log artifacts (with light header de-duplication for pidstat-style logs).
- Regenerates a consolidated checkpoint based on the consolidated results CSV (when applicable).

**Run from repo root:**
```bash
python3 utils/ldpc_sweep_aggregate_datasets.py
````

**Or, run from `utils/` (explicit repo root):**

```bash
cd utils
python3 ldpc_sweep_aggregate_datasets.py --repo-root ..
```

---

### `ldpc_sweep_seed_checkpoint.py`

Seeds (or repairs) checkpoint state for the LDPC sweep harness based on existing dataset artifacts. This is useful when:

* you have partial results from prior runs,
* a sweep was interrupted, or
* you want the harness to resume without redoing completed ablations.

The script inspects the existing output artifacts and reconstructs an appropriate “last seen” state (checkpoint) so the sweep harness can continue deterministically from the next configuration.

**Run from repo root:**

```bash
python3 utils/ldpc_sweep_seed_checkpoint.py
```

**This script does not have a repo-root argument, therefore we recommend copying it into the directory of your current running ablation study.**

```bash
cd utils
python3 ldpc_sweep_seed_checkpoint.py
```

---

## Conventions and repository layout assumptions

These utilities assume the same layout as the LDPC sweep harness:

* **Repository root** contains the primary sweep scripts and dense-sweep artifacts:

  * `sweep_ldpc.sh` and/or related harness scripts
  * top-level output artifacts (e.g., `ldpc_sionna_spark.csv`, `gpu_ldpc_sweep_stats.csv`, logs, checkpoints, etc.)

* **`baseline/`** contains:

  * `sweep_ldpc_baseline.sh` (and baseline artifacts with the same naming conventions as root artifacts)

* **`consolidated/`** is created (or overwritten) by aggregation scripts as the unified output location.

---

## Tips

* Treat `consolidated/` as a generated directory (safe to delete and regenerate).
* If you change artifact schemas (new columns, renamed fields), re-run aggregation so downstream plotting/post-processing sees a consistent dataset.
* For reproducibility, commit scripts and configuration, but avoid committing large generated artifacts unless your repo policy explicitly requires it.

