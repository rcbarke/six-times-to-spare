#!/usr/bin/env python3
"""
ldpc_cpu_gpu_benchmark.py

Compare LDPC5G decode performance on Grace CPU (/CPU:0) and
GB10 GPU (/GPU:0) using Sionna 1.2.1 PHY/SYS on DGX Spark.

- Builds a 5G-style LDPC + 16-QAM + AWGN chain.
- Generates one large dataset of LLRs.
- Times ONLY the LDPC5G decode on CPU and GPU.
- Reports latency, throughput (Mbit/s of info bits), and speedups.
- Optionally appends results to a CSV file for sweeps/analytics.

Run inside your sionna-gpu venv, e.g.:
    (sionna-gpu) python3 ldpc_cpu_gpu_benchmark.py \
        --num-codewords 8192 --num-iter 20 --repeat 10 \
        --csv-path ldpc_results.csv --label "grace_gb10_baseline"

References:
    [1] J. Hoydis et al., "Sionna: An Open-Source Library for Next-Generation
        Physical Layer Research," arXiv:2203.11854, 2022.
    [2] N. Horrocks, "Jumpstarting Link-Level Simulations with NVIDIA Sionna,"
        NVIDIA Developer Blog, 2022.
    [3] J. Dai et al., "Multi-Gbps LDPC Decoder on GPU Devices," Electronics,
        vol. 11, no. 21, 3447, 2022.
    [4] Z. Lu, "Implementing a GPU-Assisted LDPC Decoder for 5G New Radio,"
        MASc Thesis, Univ. of Toronto, 2023.
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # keep TF quiet-ish

import argparse
import csv
import socket
import time
from datetime import datetime

import numpy as np
import tensorflow as tf
import sionna

from sionna.phy.mapping import (
    Constellation,
    Mapper,
    Demapper,
    BinarySource,
)
from sionna.phy.fec.ldpc import LDPC5GEncoder, LDPC5GDecoder
from sionna.phy.utils import ebnodb2no


def configure_tf(cpu_threads: int | None = None):
    """Optional TF threading tweaks for Grace."""
    if cpu_threads is not None and cpu_threads > 0:
        tf.config.threading.set_intra_op_parallelism_threads(cpu_threads)
        tf.config.threading.set_inter_op_parallelism_threads(cpu_threads)

    # Silence most logs
    tf.get_logger().setLevel("ERROR")


def print_env():
    print("=== Environment ===")
    print("Host      :", socket.gethostname())
    print("Datetime  :", datetime.now().isoformat(timespec="seconds"))
    print("TensorFlow:", tf.__version__)
    print("Sionna    :", sionna.__version__)
    print("GPUs      :", tf.config.list_physical_devices("GPU"))
    print()


def awgn_manual(x: tf.Tensor, no: tf.Tensor) -> tf.Tensor:
    """
    Complex AWGN with noise spectral density No (per complex dim).
    """
    no = tf.cast(no, tf.float32)
    sigma = tf.sqrt(no / 2.0)
    noise_real = tf.random.normal(tf.shape(x), stddev=sigma, dtype=tf.float32)
    noise_imag = tf.random.normal(tf.shape(x), stddev=sigma, dtype=tf.float32)
    w = tf.complex(noise_real, noise_imag)
    return tf.cast(x, tf.complex64) + w


def build_chain(k: int, rate: float, m: int, num_iter: int):
    """
    Build the LDPC5G + 16-QAM chain.

    k   : info bits per codeword
    rate: code rate (k/n)
    m   : bits per symbol (4 -> 16-QAM)
    """
    n = int(k / rate)
    if n % m != 0:
        raise ValueError("n must be divisible by m for QAM mapping.")

    print(f"Using LDPC5G with k={k}, n={n}, rate={rate:.3f}, M=2^{m}")

    source = BinarySource()
    const = Constellation("qam", num_bits_per_symbol=m)
    mapper = Mapper(constellation=const)
    demapper = Demapper("app", constellation=const)

    encoder = LDPC5GEncoder(
        k=k,
        n=n,
        num_bits_per_symbol=m,
    )
    decoder = LDPC5GDecoder(
        encoder,
        hard_out=True,       # return hard bits
        num_iter=num_iter,   # decoder iterations
    )

    return {
        "source": source,
        "const": const,
        "mapper": mapper,
        "demapper": demapper,
        "encoder": encoder,
        "decoder": decoder,
        "k": k,
        "n": n,
        "rate": rate,
        "m": m,
    }


def generate_dataset(chain: dict,
                     num_codewords: int,
                     ebno_db: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate a dataset of (u, llr) using the full chain.

    Returns:
        u_np   : shape [num_codewords, k]  (info bits)
        llr_np : shape [num_codewords, n]  (LLRs for LDPC decoder)
    """
    source   = chain["source"]
    mapper   = chain["mapper"]
    demapper = chain["demapper"]
    encoder  = chain["encoder"]
    k        = chain["k"]
    n        = chain["n"]
    rate     = chain["rate"]
    m        = chain["m"]

    # Eb/N0 -> No using Sionna utility
    ebno_tf = tf.constant(ebno_db, dtype=tf.float32)
    no = ebnodb2no(ebno_tf, num_bits_per_symbol=m, coderate=rate)

    print(f"Generating dataset: num_codewords={num_codewords}, Eb/N0={ebno_db} dB")

    u = source([num_codewords, k])      # (B, k)
    c = encoder(u)                      # (B, n)
    s = mapper(c)                       # (B, n/m) complex
    y = awgn_manual(s, no)              # (B, n/m) complex
    llr = demapper(y, no)               # (B, n) LLRs

    u_np = u.numpy()
    llr_np = llr.numpy()
    print("Dataset shapes: u", u_np.shape, ", llr", llr_np.shape)
    print()
    return u_np, llr_np


def benchmark_device(device_str: str,
                     decoder,
                     llr_np: np.ndarray,
                     cfg) -> dict:
    """
    Time repeated LDPC5G decodes on a given TF device (CPU or GPU).

    cfg: argparse.Namespace with fields:
         k, num_codewords, repeat
    """
    print(f"--- Benchmarking on {device_str} ---")

    llr_tf = tf.convert_to_tensor(llr_np, dtype=tf.float32)

    with tf.device(device_str):
        llr_dev = tf.identity(llr_tf)

        @tf.function
        def decode_once(llr_in):
            return decoder(llr_in)

        # Warm-up
        _ = decode_once(llr_dev)

        start = time.perf_counter()
        for _ in range(cfg.repeat):
            _ = decode_once(llr_dev)
        # Ensure all work is done before timing stops
        try:
            tf.experimental.async_wait()
        except AttributeError:
            pass
        end = time.perf_counter()

    elapsed = end - start
    avg_latency = elapsed / cfg.repeat
    total_info_bits = cfg.num_codewords * cfg.k * cfg.repeat
    throughput_mbps = total_info_bits / elapsed / 1e6

    print(f"Total time: {elapsed:.6f} s for "
          f"{cfg.repeat} decodes of {cfg.num_codewords} codewords")
    print(f"Throughput: {throughput_mbps:.2f} Mbit/s (info bits)")
    print()

    return {
        "latency_s": avg_latency,
        "throughput_mbps": throughput_mbps,
    }


def append_results_to_csv(csv_path: str, cfg, chain: dict, results: dict):
    """
    Append a single summary row (CPU + GPU) to a CSV file.

    If the file does not exist or is empty, write a header first.
    """
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)

    fieldnames = [
        "timestamp",
        "host",
        "label",
        "k",
        "n",
        "rate",
        "m",
        "num_codewords",
        "ebno_db",
        "num_iter",
        "repeat",
        "cpu_latency_s",
        "cpu_throughput_mbps",
        "gpu_latency_s",
        "gpu_throughput_mbps",
        "latency_speedup_cpu_over_gpu",
        "throughput_speedup_gpu_over_cpu",
    ]

    file_exists = os.path.exists(csv_path) and os.path.getsize(csv_path) > 0

    cpu_lat = results["cpu"]["latency_s"]
    cpu_thr = results["cpu"]["throughput_mbps"]
    gpu_lat = results.get("gpu", {}).get("latency_s", float("nan"))
    gpu_thr = results.get("gpu", {}).get("throughput_mbps", float("nan"))

    if "gpu" in results and gpu_lat > 0 and cpu_thr > 0:
        speedup_lat = cpu_lat / gpu_lat
        speedup_thr = gpu_thr / cpu_thr
    else:
        speedup_lat = float("nan")
        speedup_thr = float("nan")

    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "host": socket.gethostname(),
        "label": cfg.label,
        "k": cfg.k,
        "n": chain["n"],
        "rate": cfg.rate,
        "m": cfg.m,
        "num_codewords": cfg.num_codewords,
        "ebno_db": cfg.ebno_db,
        "num_iter": cfg.num_iter,
        "repeat": cfg.repeat,
        "cpu_latency_s": cpu_lat,
        "cpu_throughput_mbps": cpu_thr,
        "gpu_latency_s": gpu_lat,
        "gpu_throughput_mbps": gpu_thr,
        "latency_speedup_cpu_over_gpu": speedup_lat,
        "throughput_speedup_gpu_over_cpu": speedup_thr,
    }

    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"Appended results to {csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="LDPC5G CPU vs GPU benchmark on DGX Spark (GB10) using Sionna."
    )
    parser.add_argument("--k", type=int, default=512,
                        help="Number of information bits per codeword (k).")
    parser.add_argument("--rate", type=float, default=0.5,
                        help="LDPC code rate (k/n).")
    parser.add_argument("--m", type=int, default=4,
                        help="Bits per QAM symbol (4 -> 16-QAM).")
    parser.add_argument("--num-codewords", type=int, default=4096,
                        help="Number of codewords to decode.")
    parser.add_argument("--ebno-db", type=float, default=4.0,
                        help="Eb/N0 in dB for dataset generation.")
    parser.add_argument("--num-iter", type=int, default=10,
                        help="Number of LDPC decoder iterations.")
    parser.add_argument("--repeat", type=int, default=10,
                        help="Number of repeated decodes per device.")
    parser.add_argument("--cpu-threads", type=int, default=None,
                        help="Optional: limit TF CPU threads (Grace).")
    parser.add_argument("--no-gpu", action="store_true",
                        help="Skip GPU benchmark even if a GPU is present.")
    parser.add_argument("--csv-path", type=str, default=None,
                        help="If set, append results to this CSV file.")
    parser.add_argument("--label", type=str, default="",
                        help="Optional label for this run (experiment ID).")

    cfg = parser.parse_args()

    configure_tf(cpu_threads=cfg.cpu_threads)
    print_env()

    # Build chain & dataset
    chain = build_chain(k=cfg.k, rate=cfg.rate, m=cfg.m, num_iter=cfg.num_iter)
    u_np, llr_np = generate_dataset(chain, cfg.num_codewords, cfg.ebno_db)

    decoder = chain["decoder"]
    results: dict[str, dict] = {}

    # Grace CPU benchmark
    results["cpu"] = benchmark_device("/CPU:0", decoder, llr_np, cfg)

    # GB10 GPU benchmark
    if not cfg.no_gpu and tf.config.list_physical_devices("GPU"):
        results["gpu"] = benchmark_device("/GPU:0", decoder, llr_np, cfg)
    else:
        print("No GPU detected or --no-gpu set; skipping GPU benchmark.")
        print()

    # Summary to stdout
    print("=== Summary ===")
    cpu_lat = results["cpu"]["latency_s"]
    cpu_thr = results["cpu"]["throughput_mbps"]
    print(f"CPU: latency/dec = {cpu_lat:.6f} s, "
          f"throughput = {cpu_thr:.2f} Mbit/s")

    if "gpu" in results:
        gpu_lat = results["gpu"]["latency_s"]
        gpu_thr = results["gpu"]["throughput_mbps"]

        speedup_lat = cpu_lat / gpu_lat if gpu_lat > 0 else float("inf")
        speedup_thr = gpu_thr / cpu_thr if cpu_thr > 0 else float("inf")

        print(f"GPU: latency/dec = {gpu_lat:.6f} s, "
              f"throughput = {gpu_thr:.2f} Mbit/s")
        print()
        print(f"Latency speedup (CPU / GPU): {speedup_lat:.2f}x")
        print(f"Throughput speedup (GPU / CPU): {speedup_thr:.2f}x")
    else:
        print("GPU results: N/A")

    # Optional CSV logging
    if cfg.csv_path:
        append_results_to_csv(cfg.csv_path, cfg, chain, results)

    print("\nDone.")


if __name__ == "__main__":
    main()
