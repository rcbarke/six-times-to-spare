# utils/

This directory contains **utility scripts used to manage LDPC sweep experiments and datasets** for the *Six Times to Spare* study.

The scripts here support three primary tasks:

1. **Aggregating LDPC sweep datasets**
2. **Seeding or repairing sweep checkpoints**
3. **Supervising long-running sweep jobs**

These utilities are not tied to a single hardware platform and can be used with:

- `dgx-spark/` experiments (edge platform)
- `i9-14900K-rtx-4090/` experiments (COTS comparison)

---

# Contents

## ldpc_sweep_aggregate_datasets.py

Aggregates dataset artifacts from two sweep regions:

- **baseline/**  
  small-batch regime  
  `N_cw = 1 … 1024`

- **dense sweep (repo root)**  
  dense edge regime  
  `N_cw = 2048 … 20480`

into a single **consolidated dataset spanning the full range**.

Typical workflow:

```

baseline/          → small-batch study
repo root results  → dense sweep
--------------------------------

consolidated/      → merged dataset

```

The script merges artifacts including:

```

ldpc_sionna_*.csv
gpu_ldpc_sweep_stats.csv
pid_ldpc_sweep_stats.log
ldpc_sionna_*.checkpoint

````

### Merge behavior

| Artifact | Operation |
|--------|--------|
CSV datasets | concatenated + de-duplicated |
pidstat logs | concatenated with header filtering |
other logs | appended |
checkpoint | regenerated from consolidated CSV |

### Run

From repository root:

```bash
python3 utils/ldpc_sweep_aggregate_datasets.py
````

or explicitly:

```bash
python3 utils/ldpc_sweep_aggregate_datasets.py --repo-root .
```

The merged dataset is written to:

```
dgx-spark/
```

---

## ldpc_sweep_seed_checkpoint.py

Reconstructs a **valid sweep checkpoint** from an existing dataset CSV.

This allows a sweep to **resume from the last completed configuration** if a run was interrupted.

The script parses dataset labels of the form:

```
repX_NY_IZ
```

and reconstructs:

```
LAST_REP
LAST_N
LAST_I
```

which match the expected checkpoint format used by sweep scripts.

Example output:

```
LAST_REP=2
LAST_N=20480
LAST_I=22
```

### Run

```bash
python3 utils/ldpc_sweep_seed_checkpoint.py
```

Optional arguments:

```
python3 utils/ldpc_sweep_seed_checkpoint.py results.csv checkpoint.out
```

---

## recovery_watchdog.sh

Supervises long-running LDPC sweeps inside a **tmux session**.

Purpose:

* automatically restart crashed sweeps
* preserve logs
* allow unattended long-duration runs

The watchdog monitors:

```
tmux session
tmux window
pane state
process exit codes
```

and respawns the sweep if the pane exits.

The default monitored script is:

```
sweep_ldpc_cumulative.sh
```

### Usage

```
chmod +x utils/recovery_watchdog.sh
./utils/recovery_watchdog.sh
```

Logs are written to:

```
sweep_ldpc_cumulative.watchdog.log
```

---

# Execution Context

These utilities assume the repository structure:

```
six-times-to-spare/

  dgx-spark/
      baseline/
      dense-codeword/

  i9-14900K-rtx-4090/
      ldpc_spike/

  utils/
```

Most utilities expect to be run **from the repository root**.

Example:

```
cd six-times-to-spare
python3 utils/ldpc_sweep_aggregate_datasets.py
```

---

# Notes

* `consolidated/` datasets are **generated artifacts** and can be safely regenerated.
* Utilities intentionally avoid modifying raw experiment results.
* These scripts support both **DGX Spark (edge)** and **COTS workstation** experiments.

```
