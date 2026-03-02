#!/usr/bin/env python3
"""
Post-processing for DGX Spark LDPC sweep.

Assumes the following files are in the current directory:
    - ldpc_sionna_spark.csv
    - gpu_ldpc_sweep_stats.csv
    - pid_ldpc_sweep_stats.log

Outputs:
    - fig_ldpc_throughput_vs_iter.png
    - fig_ldpc_resource_utilization.png
"""

import re
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt


# ----------------------------------------------------------------------
# Helpers to load and preprocess the three data sources
# ----------------------------------------------------------------------

def load_ldpc_results(path: str = "ldpc_sionna_spark.csv") -> pd.DataFrame:
    """Load main LDPC benchmark results."""
    df = pd.read_csv(path)

    # Per-codeword latency in ms for convenience
    df["cpu_ms_per_cb"] = df["cpu_latency_s"] / df["num_codewords"] * 1e3
    df["gpu_ms_per_cb"] = df["gpu_latency_s"] / df["num_codewords"] * 1e3
    df["speedup"] = df["throughput_speedup_gpu_over_cpu"]

    return df


def load_gpu_stats(path: str = "gpu_ldpc_sweep_stats.csv") -> pd.DataFrame:
    """Load GPU utilization and power from nvidia-smi CSV."""
    gpu = pd.read_csv(path)

    # Strip leading/trailing spaces from column names
    gpu = gpu.rename(columns=lambda c: c.strip())

    # Parse timestamp ("YYYY/MM/DD HH:MM:SS.mmm")
    gpu["ts"] = pd.to_datetime(gpu["timestamp"], format="%Y/%m/%d %H:%M:%S.%f")

    return gpu


def parse_pid_line(line: str, date_str: str) -> dict | None:
    """
    Parse one pidstat line for the python3 process.

    Example line:
    '10:48:01 PM  1001      7791  143.00   24.00    0.00    0.00  ...  python3'
    """
    if "python" not in line:
        return None

    parts = re.split(r"\s+", line.strip())
    if len(parts) < 6:
        return None

    time_str = parts[0] + " " + parts[1]  # '10:48:01 PM'
    uid = int(parts[2])
    pid = int(parts[3])

    try:
        usr = float(parts[4])
        system = float(parts[5])
    except ValueError:
        return None

    ts = datetime.strptime(
        f"{date_str} {time_str}",
        "%Y-%m-%d %I:%M:%S %p"
    )

    return {
        "timestamp": ts,
        "uid": uid,
        "pid": pid,
        "cpu_user": usr,
        "cpu_system": system,
        "cpu_total": usr + system,  # sum in percent-of-one-core
    }


def load_cpu_stats(
    path: str = "pid_ldpc_sweep_stats.log",
    date_str: str = "2025-11-29",
) -> pd.DataFrame:
    """Load per-PID CPU stats for the python3 LDPC process."""
    records: list[dict] = []

    with open(path, "r") as f:
        for line in f:
            rec = parse_pid_line(line, date_str)
            if rec is not None:
                records.append(rec)

    if not records:
        raise RuntimeError("No python3 lines parsed from pidstat log.")

    df = pd.DataFrame(records)
    df["cpu_cores"] = df["cpu_total"] / 100.0  # 100% ~ 1 full core

    return df


# ----------------------------------------------------------------------
# Plotting functions
# ----------------------------------------------------------------------

def plot_throughput_vs_iter(df: pd.DataFrame, out_path: str) -> None:
    """
    Plot average CPU vs GPU throughput as a function of LDPC iterations.
    """
    agg = (
        df.groupby("num_iter", as_index=False)
          .agg(
              cpu_thr=("cpu_throughput_mbps", "mean"),
              gpu_thr=("gpu_throughput_mbps", "mean"),
              speedup=("speedup", "mean"),
          )
    )

    plt.figure(figsize=(6, 4))
    plt.plot(agg["num_iter"], agg["cpu_thr"], marker="o", label="Grace CPU")
    plt.plot(agg["num_iter"], agg["gpu_thr"], marker="o", label="GB10 GPU")

    plt.xlabel("LDPC decoder iterations (num_iter)")
    plt.ylabel("Throughput [Mbit/s]")
    plt.title("LDPC5G throughput vs iterations on DGX Spark")
    plt.grid(True, which="both", axis="both")
    plt.legend()

    # Annotate GPU curve with average speedup per point
    for _, row in agg.iterrows():
        x = row["num_iter"]
        y = row["gpu_thr"]
        plt.text(
            x,
            y,
            f"{row['speedup']:.1f}×",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()

def plot_resource_utilization(
    gpu: pd.DataFrame,
    cpu: pd.DataFrame,
    out_path: str,
) -> None:
    """
    Plot histograms of CPU core usage and GPU utilization during active periods.
    """
    # Active GPU samples: utilization > 5%
    gpu_active = gpu[gpu["utilization.gpu [%]"] > 5]

    # Active CPU samples: LDPC python process clearly running
    cpu_active = cpu[cpu["cpu_total"] > 50]

    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    # CPU histogram (in units of "active cores")
    axes[0].hist(cpu_active["cpu_cores"], bins=20)
    axes[0].set_xlabel("Approx. Grace CPU cores used\n(LDPC python3 process)")
    axes[0].set_ylabel("Count")
    axes[0].set_title("CPU utilization during LDPC sweep")
    axes[0].grid(True, axis="y")

    # GPU histogram (utilization percent)
    axes[1].hist(gpu_active["utilization.gpu [%]"], bins=20)
    axes[1].set_xlabel("GB10 GPU utilization [%]\n(nvidia-smi, active samples)")
    axes[1].set_ylabel("Count")
    axes[1].set_title("GPU utilization during LDPC sweep")
    axes[1].grid(True, axis="y")

    # Put the suptitle inside the figure bounds and reserve some top space
    fig.suptitle("Resource usage for LDPC5G decoding on DGX Spark", fontsize=12)
    # rect=[left, bottom, right, top] -> leave 7% headroom for the suptitle
    fig.tight_layout(rect=[0, 0, 1, 0.93])

    fig.savefig(out_path, dpi=300)
    plt.close(fig)

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def main() -> None:
    ldpc_df = load_ldpc_results("ldpc_sionna_spark.csv")
    gpu_df = load_gpu_stats("gpu_ldpc_sweep_stats.csv")
    cpu_df = load_cpu_stats("pid_ldpc_sweep_stats.log", date_str="2025-11-29")

    # Figure 1: throughput vs iterations
    plot_throughput_vs_iter(ldpc_df, "fig_ldpc_throughput_vs_iter.png")

    # Figure 2: CPU vs GPU utilization histograms
    plot_resource_utilization(
        gpu_df,
        cpu_df,
        "fig_ldpc_resource_utilization.png",
    )

    # Optional: print a concise summary to stdout
    avg_speedup = ldpc_df["speedup"].mean()
    print(f"Average GPU/CPU throughput speedup over all configs: {avg_speedup:.2f}×")

    cpu_mean_cores = cpu_df["cpu_cores"].mean()
    print(f"Mean cores used by LDPC python3 process: {cpu_mean_cores:.1f} / 20")

    gpu_active = gpu_df[gpu_df["utilization.gpu [%]"] > 5]
    print(
        "GPU active-period stats: "
        f"mean util={gpu_active['utilization.gpu [%]'].mean():.1f}%, "
        f"mean power={gpu_active['power.draw [W]'].mean():.2f} W"
    )


if __name__ == "__main__":
    main()

