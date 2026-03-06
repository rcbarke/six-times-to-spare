#!/usr/bin/env python3
"""
Combine DGX Spark and COTS LDPC benchmark results into shared comparison plots.

Expected layout:
    .
    ├── dgx-spark/
    │   └── ldpc_sionna_spark.csv
    └── i9-14900K-rtx-4090/
        └── ldpc_sionna_cots.csv

Outputs:
    - fig_combined_throughput_vs_iter.png
    - fig_combined_throughput_vs_codewords.png
"""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


DGX_DIR = Path("dgx-spark")
COTS_DIR = Path("i9-14900K-rtx-4090")

DGX_CSV = DGX_DIR / "ldpc_sionna_spark.csv"
COTS_CSV = COTS_DIR / "ldpc_sionna_cots.csv"


def load_ldpc_results(path: Path) -> pd.DataFrame:
    """Load LDPC benchmark results and validate required columns."""
    df = pd.read_csv(path)

    required_cols = {
        "num_iter",
        "num_codewords",
        "cpu_throughput_mbps",
        "gpu_throughput_mbps",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")

    return df


def aggregate_by_iter(df: pd.DataFrame) -> pd.DataFrame:
    """Average CPU/GPU throughput by LDPC iteration count."""
    return (
        df.groupby("num_iter", as_index=False)
        .agg(
            cpu_thr=("cpu_throughput_mbps", "mean"),
            gpu_thr=("gpu_throughput_mbps", "mean"),
        )
        .sort_values("num_iter")
    )


def aggregate_by_codewords(df: pd.DataFrame) -> pd.DataFrame:
    """Average CPU/GPU throughput by number of codewords."""
    return (
        df.groupby("num_codewords", as_index=False)
        .agg(
            cpu_thr=("cpu_throughput_mbps", "mean"),
            gpu_thr=("gpu_throughput_mbps", "mean"),
        )
        .sort_values("num_codewords")
    )


def plot_throughput_vs_iter(
    dgx_df: pd.DataFrame,
    cots_df: pd.DataFrame,
    out_path: str = "fig_combined_throughput_vs_iter.png",
) -> None:
    """Plot all four throughput trendlines versus LDPC iterations."""
    dgx = aggregate_by_iter(dgx_df)
    cots = aggregate_by_iter(cots_df)

    plt.figure(figsize=(8, 5))

    plt.plot(
        dgx["num_iter"],
        dgx["cpu_thr"],
        marker="o",
        label="DGX Spark CPU",
    )
    plt.plot(
        dgx["num_iter"],
        dgx["gpu_thr"],
        marker="o",
        label="DGX Spark GPU",
    )
    plt.plot(
        cots["num_iter"],
        cots["cpu_thr"],
        marker="s",
        label="i9-14900K CPU",
    )
    plt.plot(
        cots["num_iter"],
        cots["gpu_thr"],
        marker="s",
        label="RTX 4090 GPU",
    )

    plt.xlabel("LDPC decoder iterations (num_iter)")
    plt.ylabel("Throughput [Mbit/s]")
    plt.title("LDPC5G throughput vs iterations: DGX Spark vs COTS")
    plt.grid(True, which="both", axis="both")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()


def plot_throughput_vs_codewords(
    dgx_df: pd.DataFrame,
    cots_df: pd.DataFrame,
    out_path: str = "fig_combined_throughput_vs_codewords.png",
) -> None:
    """Plot all four throughput trendlines versus number of codewords."""
    dgx = aggregate_by_codewords(dgx_df)
    cots = aggregate_by_codewords(cots_df)

    plt.figure(figsize=(8, 5))

    plt.plot(
        dgx["num_codewords"],
        dgx["cpu_thr"],
        marker="o",
        label="Grace ARM CPU",
    )
    plt.plot(
        dgx["num_codewords"],
        dgx["gpu_thr"],
        marker="o",
        label="GB10 GPU",
    )
    plt.plot(
        cots["num_codewords"],
        cots["cpu_thr"],
        marker="s",
        label="i9-14900K CPU",
    )
    plt.plot(
        cots["num_codewords"],
        cots["gpu_thr"],
        marker="s",
        label="RTX 4090 GPU",
    )

    plt.xlabel("Number of codewords (N_cw)")
    plt.ylabel("Throughput [Mbit/s]")
    plt.title("LDPC5G throughput vs N_cw: DGX Spark vs COTS")
    plt.grid(True, which="both", axis="both")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_path, dpi=300)
    plt.close()


def main() -> None:
    if not DGX_CSV.exists():
        raise FileNotFoundError(f"Missing DGX CSV: {DGX_CSV}")
    if not COTS_CSV.exists():
        raise FileNotFoundError(f"Missing COTS CSV: {COTS_CSV}")

    dgx_df = load_ldpc_results(DGX_CSV)
    cots_df = load_ldpc_results(COTS_CSV)

    plot_throughput_vs_iter(dgx_df, cots_df)
    plot_throughput_vs_codewords(dgx_df, cots_df)

    print("Wrote:")
    print("  - fig_combined_throughput_vs_iter.png")
    print("  - fig_combined_throughput_vs_codewords.png")


if __name__ == "__main__":
    main()
