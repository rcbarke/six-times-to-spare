#!/usr/bin/env python3
"""
Minimal end-to-end Sionna sanity check on GB10:

- Binary source -> LDPC5G encoder
- 16-QAM mapper
- AWGN (manual, in TF)
- Demapper -> LDPC5G decoder
- BER vs Eb/N0
- Optional 3D constellation plotting

Run inside your sionna-gpu venv:
    (sionna-gpu) python3 sionna_e2e_ldpc_awgn.py
"""

import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # 0=all, 1=INFO off, 2=WARNING off, 3=ERROR off

import tensorflow as tf
from absl import logging as absl_logging

absl_logging.set_verbosity(absl_logging.ERROR)
import numpy as np
import sionna

from sionna.phy.mapping import (
    Constellation,
    Mapper,
    Demapper,
    BinarySource,
)
from sionna.phy.fec.ldpc import LDPC5GEncoder, LDPC5GDecoder
from sionna.phy.utils import ebnodb2no

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


def configure_tf():
    # Optional: ensure TF uses GPU 0 and enables memory growth
    gpus = tf.config.list_physical_devices('GPU')
    if gpus:
        try:
            tf.config.set_visible_devices(gpus[0], 'GPU')
            tf.config.experimental.set_memory_growth(gpus[0], True)
        except RuntimeError as e:
            print("TF GPU config warning:", e)

    tf.get_logger().setLevel('ERROR')


def print_env_info():
    print("=== Environment ===")
    print("TensorFlow:", tf.__version__)
    print("Sionna    :", sionna.__version__)
    print("GPUs      :", tf.config.list_physical_devices("GPU"))
    print()


def build_chain(k=512, rate=0.5, num_bits_per_symbol=4):
    """
    Build LDPC5G + 16QAM chain.

    k   : info bits per codeword
    rate: k/n
    num_bits_per_symbol: 4 -> 16QAM
    """
    n = int(k / rate)
    if n % num_bits_per_symbol != 0:
        raise ValueError("n must be divisible by num_bits_per_symbol for mapping.")

    print(f"Using LDPC5G with k={k}, n={n}, rate={rate:.3f}, M=2^{num_bits_per_symbol} (16-QAM)")

    source = BinarySource()
    const = Constellation("qam", num_bits_per_symbol=num_bits_per_symbol)
    mapper = Mapper(constellation=const)
    demapper = Demapper("app", constellation=const)

    encoder = LDPC5GEncoder(
        k=k,
        n=n,
        num_bits_per_symbol=num_bits_per_symbol,
    )
    decoder = LDPC5GDecoder(
        encoder,
        hard_out=True,     # return hard bits 0/1
        num_iter=25,       # modest iteration count
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
        "m": num_bits_per_symbol,
    }


def awgn_manual(x, no):
    """
    Complex AWGN with given noise spectral density No.

    Assumes E[|x|^2] ~= 1 (Constellation is normalized),
    so noise variance per complex dimension is No.

    x : complex tf.Tensor
    no: tf.Tensor scalar (float32) - noise spectral density
    """
    no = tf.cast(no, tf.float32)
    # For complex noise: variance per real dim = No/2
    sigma = tf.sqrt(no / 2.0)
    noise_real = tf.random.normal(tf.shape(x), mean=0.0, stddev=sigma, dtype=tf.float32)
    noise_imag = tf.random.normal(tf.shape(x), mean=0.0, stddev=sigma, dtype=tf.float32)
    w = tf.complex(noise_real, noise_imag)
    return tf.cast(x, tf.complex64) + w


def run_ber_sweep(chain, ebno_dbs, batch_size=256, num_batches=40):
    """
    Measure *info-bit* BER vs Eb/N0.

    We compare decoded info bits vs original info bits (length k).
    """
    source   = chain["source"]
    mapper   = chain["mapper"]
    demapper = chain["demapper"]
    encoder  = chain["encoder"]
    decoder  = chain["decoder"]
    k        = chain["k"]
    n        = chain["n"]
    rate     = chain["rate"]
    m        = chain["m"]

    ber_results = []

    for ebno_db in ebno_dbs:
        total_err  = 0
        total_bits = 0

        # Compute No for this Eb/N0 (per complex dim)
        ebno_tf = tf.constant(ebno_db, dtype=tf.float32)
        no = ebnodb2no(ebno_tf, num_bits_per_symbol=m, coderate=rate)

        for _ in range(num_batches):
            # Run the whole chain on GPU: u -> c -> s -> y -> llr -> u_hat
            with tf.device("/GPU:0"):
                u = source([batch_size, k])   # (B, k)
                c = encoder(u)                # (B, n)
                s = mapper(c)                 # (B, n/m) complex

                y   = awgn_manual(s, no)      # (B, n/m) complex
                llr = demapper(y, no)         # (B, n) LLRs
                u_hat = decoder(llr)          # (B, k) hard bits (info bits)

            # Compare info bits
            err = tf.math.count_nonzero(tf.not_equal(u_hat, u))
            total_err  += int(err.numpy())
            total_bits += batch_size * k

        ber = total_err / total_bits
        ber_results.append(ber)
        print(f"Eb/N0 = {ebno_db:4.1f} dB : BER(info bits) = {ber:.3e}")

    return ber_results

def plot_constellation_3d(const):
    """Simple 3D scatter of the 16-QAM constellation."""
    pts = const.points.numpy()  # complex64
    x = np.real(pts)
    y = np.imag(pts)
    z = np.zeros_like(x)

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x, y, z)
    ax.set_xlabel("In-phase")
    ax.set_ylabel("Quadrature")
    ax.set_zlabel("Dummy axis")
    ax.set_title("Sionna 16-QAM constellation (3D sanity check)")
    plt.tight_layout()
    plt.show()


def main():
    configure_tf()
    print_env_info()

    # Build PHY chain
    chain = build_chain(
        k=512,
        rate=0.5,
        num_bits_per_symbol=4,  # 16-QAM
    )

    # Optional: visually confirm Axes3D works and Sionna's constellation looks sane
    print("\nPlotting 3D constellation (close the window to continue)...")
    plot_constellation_3d(chain["const"])

    # BER sweep
    print("\nRunning BER sweep (this will use the GB10)...")
    ebno_dbs = [0.0, 2.0, 4.0, 6.0, 8.0]
    run_ber_sweep(chain, ebno_dbs, batch_size=256, num_batches=20)


if __name__ == "__main__":
    main()

