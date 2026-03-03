#!/usr/bin/env python3
"""
ldpc_sweep_aggregate_datasets.py

Combine dataset artifacts from:
  1) repo root (dense / urban sweep)
  2) baseline/ subdirectory (lower-bound / rural sweep)

into a single consolidated dataset spanning the full N_cw range,
and write outputs to: consolidated/ (relative to repo root).

Run:
  ./aggregate_datasets
or:
  python3 aggregate_datasets

Notes:
- CSV artifacts are concatenated, de-duplicated (row-wise), and sorted when possible.
- pidstat-like logs are concatenated with simple header de-duplication.
- The consolidated checkpoint is regenerated from the consolidated results CSV.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# Pandas is optional; script still works for non-CSV artifacts without it.
try:
    import pandas as pd  # type: ignore
except Exception:
    pd = None  # type: ignore


DATA_EXT_ALLOWLIST = {".csv", ".log", ".checkpoint", ".txt"}


@dataclass(frozen=True)
class Inputs:
    repo_root: Path
    baseline_dir: Path
    out_dir: Path


def _is_repo_root(p: Path) -> bool:
    # Heuristic: require baseline/ to exist to avoid accidental runs in wrong cwd.
    return (p / "baseline").is_dir()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _collect_candidate_files(repo_root: Path, baseline_dir: Path) -> List[str]:
    """
    Gather filenames to consider:
      - any allowlisted data file in repo root
      - any allowlisted data file in baseline/
    """
    names = set()

    for d in (repo_root, baseline_dir):
        if not d.is_dir():
            continue
        for fp in d.iterdir():
            if fp.is_file() and fp.suffix in DATA_EXT_ALLOWLIST:
                names.add(fp.name)

    # Always include canonical filenames if present in either location.
    for canonical in (
        "ldpc_sionna_spark.csv",
        "gpu_ldpc_sweep_stats.csv",
        "pid_ldpc_sweep_stats.log",
        "ldpc_sionna_spark.checkpoint",
    ):
        if (repo_root / canonical).exists() or (baseline_dir / canonical).exists():
            names.add(canonical)

    return sorted(names)


def _merge_csv(files: List[Path], out_path: Path) -> None:
    if pd is None:
        raise RuntimeError(
            "pandas is required to merge CSV artifacts, but it is not available."
        )

    dfs = []
    for f in files:
        if not f.exists():
            continue
        try:
            dfs.append(pd.read_csv(f))
        except Exception as e:
            raise RuntimeError(f"Failed reading CSV: {f} ({e})") from e

    if not dfs:
        return

    df = pd.concat(dfs, ignore_index=True)

    # Row-wise dedupe (safe even if schema differs slightly between runs)
    df = df.drop_duplicates()

    # Try to sort by common sweep keys if present
    sort_cols = []
    for c in ("num_codewords", "N_cw", "num_iter", "I", "repeat", "timestamp"):
        if c in df.columns:
            sort_cols.append(c)

    if "timestamp" in df.columns:
        # attempt timestamp parse for stable ordering without being strict
        try:
            df["_ts"] = pd.to_datetime(df["timestamp"], errors="coerce")
            # Put parsed timestamp near the end to break ties if num_codewords/num_iter exist
            sort_cols = [c for c in sort_cols if c != "timestamp"]
            sort_cols.append("_ts")
        except Exception:
            pass

    if sort_cols:
        try:
            df = df.sort_values(sort_cols, kind="mergesort").reset_index(drop=True)
        except Exception:
            # If sorting fails due to mixed types, just skip sorting.
            pass

    if "_ts" in df.columns:
        df = df.drop(columns=["_ts"])

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)


def _merge_pidstat_logs(files: List[Path], out_path: Path) -> None:
    """
    Concatenate pidstat-like logs while skipping repeated headers.

    This is intentionally heuristic; pidstat output formats vary across distros.
    """
    header_patterns = (
        re.compile(r"^Linux\s"),            # "Linux 6.x ..."
        re.compile(r"^\s*#\s*Time"),        # "# Time ..."
        re.compile(r"^\s*Time\s+UID"),      # "Time UID PID ..."
        re.compile(r"^\s*UID\s+PID"),       # "UID PID ..."
        re.compile(r"^\s*Average:\s*$"),    # "Average:"
    )

    seen_header_lines = set()
    out_lines: List[str] = []

    for idx, f in enumerate(files):
        if not f.exists():
            continue
        text = _read_text(f)
        lines = text.splitlines()

        for line in lines:
            is_headerish = any(p.search(line) for p in header_patterns)
            if is_headerish:
                # de-dup repeated header lines across concatenated logs
                key = line.strip()
                if key in seen_header_lines:
                    continue
                seen_header_lines.add(key)

            out_lines.append(line)

        # Ensure a newline boundary between sources
        if out_lines and out_lines[-1].strip() != "":
            out_lines.append("")

    _write_text(out_path, "\n".join(out_lines).rstrip() + "\n")


def _merge_text_concat(files: List[Path], out_path: Path) -> None:
    chunks = []
    for f in files:
        if f.exists():
            chunks.append(_read_text(f).rstrip() + "\n")
    if not chunks:
        return
    _write_text(out_path, "\n".join(chunks).rstrip() + "\n")


def _regenerate_checkpoint_from_results(results_csv: Path, out_checkpoint: Path) -> None:
    """
    Produce a checkpoint file in the same format used by sweep scripts:
        LAST_REP=<max repeat>
        LAST_N=<max num_codewords>
        LAST_I=<max num_iter>
    """
    if not results_csv.exists():
        return

    if pd is None:
        # Best effort fallback: do not write checkpoint without pandas.
        return

    df = pd.read_csv(results_csv)

    # Accept either naming convention
    rep_col = "repeat" if "repeat" in df.columns else None
    n_col = "num_codewords" if "num_codewords" in df.columns else ("N_cw" if "N_cw" in df.columns else None)
    i_col = "num_iter" if "num_iter" in df.columns else ("I" if "I" in df.columns else None)

    if not (rep_col and n_col and i_col):
        return

    def _safe_max(series):
        try:
            return int(pd.to_numeric(series, errors="coerce").max())
        except Exception:
            return None

    last_rep = _safe_max(df[rep_col])
    last_n = _safe_max(df[n_col])
    last_i = _safe_max(df[i_col])

    if last_rep is None or last_n is None or last_i is None:
        return

    content = f"LAST_REP={last_rep}\nLAST_N={last_n}\nLAST_I={last_i}\n"
    _write_text(out_checkpoint, content)


def _copy_if_single_source(src_candidates: List[Path], out_path: Path) -> None:
    """
    If the artifact exists in exactly one place, copy it.
    """
    existing = [p for p in src_candidates if p.exists()]
    if len(existing) != 1:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(existing[0].read_bytes())


def aggregate(inputs: Inputs, verbose: bool = True) -> None:
    repo_root = inputs.repo_root
    baseline_dir = inputs.baseline_dir
    out_dir = inputs.out_dir

    out_dir.mkdir(parents=True, exist_ok=True)

    filenames = _collect_candidate_files(repo_root, baseline_dir)

    def vprint(msg: str) -> None:
        if verbose:
            print(msg)

    vprint(f"[aggregate_datasets] repo_root      = {repo_root}")
    vprint(f"[aggregate_datasets] baseline_dir   = {baseline_dir}")
    vprint(f"[aggregate_datasets] out_dir        = {out_dir}")
    vprint(f"[aggregate_datasets] artifacts      = {len(filenames)}")

    for name in filenames:
        root_fp = repo_root / name
        base_fp = baseline_dir / name
        out_fp = out_dir / name

        sources = [p for p in (base_fp, root_fp) if p.exists()]  # baseline first, then root
        if not sources:
            continue

        # Special handling by filename / extension
        if name.endswith(".csv"):
            vprint(f"  - merge CSV: {name} ({', '.join(str(p.relative_to(repo_root)) if p.is_relative_to(repo_root) else str(p) for p in sources)})")
            _merge_csv(sources, out_fp)
            continue

        if name.endswith("pid_ldpc_sweep_stats.log") or name.endswith(".log"):
            # pidstat log: header de-dupe; other .log: plain concat.
            if name == "pid_ldpc_sweep_stats.log":
                vprint(f"  - merge pidstat log: {name}")
                _merge_pidstat_logs(sources, out_fp)
            else:
                vprint(f"  - concat log: {name}")
                _merge_text_concat(sources, out_fp)
            continue

        if name.endswith(".checkpoint"):
            # We regenerate after CSV merge; skip here to avoid stale state.
            vprint(f"  - skip direct checkpoint merge: {name} (will regenerate)")
            continue

        # Fallback: copy if only exists in one place.
        vprint(f"  - copy if single-source: {name}")
        _copy_if_single_source([base_fp, root_fp], out_fp)

    # Regenerate consolidated checkpoint from consolidated results CSV if present.
    consolidated_results = out_dir / "ldpc_sionna_spark.csv"
    consolidated_checkpoint = out_dir / "ldpc_sionna_spark.checkpoint"
    if consolidated_results.exists():
        vprint("  - regenerate checkpoint from consolidated results CSV")
        _regenerate_checkpoint_from_results(consolidated_results, consolidated_checkpoint)

    vprint("[aggregate_datasets] done.")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Aggregate baseline/ and root dataset artifacts into consolidated/.")
    ap.add_argument(
        "--repo-root",
        default=".",
        help="Path to the repository root (default: current directory).",
    )
    ap.add_argument(
        "--baseline-subdir",
        default="baseline",
        help='Baseline subdirectory relative to repo root (default: "baseline").',
    )
    ap.add_argument(
        "--out-subdir",
        default="consolidated",
        help='Output subdirectory relative to repo root (default: "consolidated").',
    )
    ap.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()

    if not _is_repo_root(repo_root):
        print(
            f"ERROR: {repo_root} does not look like repo root (expected a baseline/ directory).",
            file=sys.stderr,
        )
        return 2

    baseline_dir = (repo_root / args.baseline_subdir).resolve()
    out_dir = (repo_root / args.out_subdir).resolve()

    aggregate(
        Inputs(repo_root=repo_root, baseline_dir=baseline_dir, out_dir=out_dir),
        verbose=not args.quiet,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
