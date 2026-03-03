# Running Sionna 1.2.1 on NVIDIA DGX Spark (GB10)

> **Status:** confirmed working as of **November 2025** on a DGX Spark with an
> NVIDIA **GB10** superchip and Python 3.12.

Sionna’s standard `pip install sionna` workflow currently conflicts with the
**GB10–enabled TensorFlow build** from NGC:

* Sionna 1.2.1 declares the dependency  
  `tensorflow!=2.16,!=2.17,>=2.14`, so `pip` tries to pull **TF 2.20.0**.
* The GB10 is only supported today by NVIDIA’s own wheel  
  `nvidia-tensorflow==2.17.0+nv25.2` installed from NGC:
  ```bash
  pip install "nvidia-tensorflow[horovod]" \
      --extra-index-url=https://pypi.ngc.nvidia.com/
  ```
* Installing Sionna **with** dependencies will overwrite that TF build and/or
  fail while trying to install **Sionna‑RT** (due to a missing `mitsuba` wheel
  on aarch64).

This README documents a **known‑good** path that:

* keeps NVIDIA’s GB10‑aware TensorFlow,
* installs **Sionna 1.2.1 PHY/SYS only** (no Sionna‑RT),
* and wires up **Matplotlib 3D** so you can do constellation plots.

We validate the setup with several unit scripts in this directory, including an
end‑to‑end **LDPC5G + 16‑QAM + AWGN + BER** sanity test that runs on the GB10. 

---

## 1. Environment

Tested with:

* **Hardware**: DGX Spark, NVIDIA **GB10** (compute capability 12.1)
* **Driver / CUDA**:

  * `nvidia-smi` → driver 580.95.05, CUDA 13.0 reported by the driver
  * `inspect_tensorflow.py` shows TF built with CUDA 12.8 and cuDNN 9 and
    supports `sm_120` in `cuda_compute_capabilities`
* **Python**: 3.12.3
* **TensorFlow**: `nvidia-tensorflow==2.17.0+nv25.2` (CUDA build, TensorRT build)
* **Sionna**: `1.2.1` (PHY/SYS only)
* **SciPy / Matplotlib**: `scipy==1.16.3`, `matplotlib==3.10.7` 

Example environment checks:

```bash
(sionna-gpu) python3 check_tensorflow.py
TF version: 2.17.0
CUDA build: True
GPUs: [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]

(sionna-gpu) python3 check_sionna.py
Sionna: 1.2.1
SciPy: 1.16.3
Matplotlib: 3.10.7
TF: 2.17.0 GPUs: [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
Constellation points (first 4): [...]
```

---

## 2. Create a clean Python 3 venv (no system site‑packages)

**Do not** rely on system Python packages; mixing them with pip packages caused
Matplotlib 3D import issues.

```bash
python3 -m venv ~/sionna-gpu
source ~/sionna-gpu/bin/activate
pip install --upgrade pip
```

Verify that the venv is **isolated**:

```bash
cat ~/sionna-gpu/pyvenv.cfg
```

Expected contents:

```ini
home = /usr/bin
include-system-site-packages = false
version = 3.12.3
executable = /usr/bin/python3.12
command = /usr/bin/python3 -m venv /home/ryan/sionna-gpu
```

If you ever created the venv with `--system-site-packages`, flip
`include-system-site-packages` to `false` and re‑install Matplotlib as below.

---

## 3. Install GB10‑enabled TensorFlow from NGC

Inside the `sionna-gpu` venv:

```bash
pip install "nvidia-tensorflow[horovod]" \
    --extra-index-url=https://pypi.ngc.nvidia.com/
```

This pulls:

```text
nvidia-tensorflow-2.17.0+nv25.2-cp312-cp312-linux_aarch64.whl
...
nvidia-cudnn-cu12-9.16.0.29
nvidia-cublas-cu12-12.9.1.4
...
tensorrt-10.14.1.48.post1
```

Verify GPU visibility & build options:

```bash
(sionna-gpu) python3 inspect_tensorflow.py
Build: OrderedDict({
  'cuda_version': '12.8',
  'cudnn_version': '9',
  'cuda_compute_capabilities': ['sm_100', 'sm_120', 'sm_75', 'sm_80', 'sm_86', 'sm_87', 'compute_90'],
  'is_cuda_build': True,
  'is_tensorrt_build': True,
})
Local devices:
   /device:CPU:0 CPU
   /device:GPU:0 GPU
```

At this point, TensorFlow alone sees the GB10 and can allocate GPU memory.

---

## 4. Why plain `pip install sionna` fails on GB10

If you try:

```bash
pip install "sionna>=1.2.1"
```

you’ll hit two issues:

1. **Sionna’s TensorFlow constraint**:

   ```text
   Collecting tensorflow!=2.16,!=2.17,>=2.14 (from sionna>=1.2.1)
   ...
   ```

   which wants to install the upstream `tensorflow-2.20.0` wheel (no GB10
   support) and overwrite the NGC build.

2. **Sionna‑RT / Mitsuba on aarch64**:

   ```text
   Collecting sionna-rt==1.2.1 (from sionna>=1.2.1)
   ...
   ERROR: Could not find a version that satisfies the requirement mitsuba==3.7.1 (from sionna-rt) (from versions: none)
   ERROR: No matching distribution found for mitsuba==3.7.1
   ```

   So on aarch64, Mitsuba 3.7.1 has no wheel and building from source is out of
   scope here.

Because of this, we **skip Sionna’s dependencies entirely** and install only
the Sionna wheel while keeping NVIDIA’s TensorFlow.

---

## 5. Install Sionna 1.2.1 (PHY / SYS only)

Still inside the venv:

```bash
pip install "sionna==1.2.1" --no-deps
```

Output:

```text
Collecting sionna==1.2.1
  Downloading sionna-1.2.1-py3-none-any.whl (520 kB)
Installing collected packages: sionna
Successfully installed sionna-1.2.1
```

The `--no-deps` flag is **critical**:

* It prevents `pip` from trying to install stock `tensorflow==2.20.0`
* It avoids the failing `sionna-rt` → `mitsuba` dependency chain

Consequences:

* You get **Sionna PHY & SYS** functionality (FEC, mapping, modulation,
  channels, etc.).
* **Sionna‑RT** (ray‑tracing / geometry) is *not* installed in this recipe.

From `pip`’s point of view, Sionna’s declared deps remain “unsatisfied”; that’s
expected and safe for PHY/SYS work.

---

## 6. Manually install the remaining Python dependencies

After Sionna is installed, we satisfy only the dependencies we need:

```bash
# Core numerical + plotting deps expected by Sionna
pip install "scipy>=1.14.1" "matplotlib>=3.10" "importlib_resources>=6.4.5"

# Pillow for Matplotlib image backends
pip install pillow

# Matplotlib 3D / plotting dependencies
pip install \
    "contourpy>=1.0.1" \
    "cycler>=0.10" \
    "fonttools>=4.22.0" \
    "pyparsing>=3" \
    "python-dateutil>=2.7"
```

During these steps `pip` will continue to remind you that Sionna’s declared
dependencies (`tensorflow`, `sionna-rt`) are missing:

```text
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. ...
sionna 1.2.1 requires sionna-rt==1.2.1, which is not installed.
sionna 1.2.1 requires tensorflow!=2.16,!=2.17,>=2.14, which is not installed.
```

Those warnings are **expected**; do **not** try to “fix” them by installing
another TensorFlow or Sionna‑RT wheel, or you’ll lose GB10 support.

---

## 7. Validating the environment

This repo includes several small sanity scripts.

### 7.1 TensorFlow GPU & build sanity

* **`check_tensorflow.py`** – prints TF version, CUDA build flag and visible
  GPUs.
* **`inspect_tensorflow.py`** – dumps `tf.sysconfig.get_build_info()` and local
  devices to confirm CUDA / cuDNN / TensorRT versions and supported SMs.

Together they verify that:

* `nvidia-tensorflow` is a CUDA build (`is_cuda_build: True`),
* GB10 is visible as `/device:GPU:0`,
* and TensorRT support is compiled in (even if some dynamic libraries like
  `libnvinfer.so.10.8.0` are missing at runtime).

### 7.2 Sionna + GPU sanity

* **`check_sionna.py`** – checks Sionna, SciPy, Matplotlib versions, confirms TF
  sees the GPU, and instantiates a 16‑QAM constellation to make sure core
  Sionna PHY pieces import correctly.

Example output (trimmed):

```text
Sionna: 1.2.1
SciPy: 1.16.3
Matplotlib: 3.10.7
TF: 2.17.0 GPUs: [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]
Constellation points (first 4): [0.3162+0.3162j ...]
```

### 7.3 Matplotlib 3D sanity

* **`check_matplotlib_3d.py`** – forces a 3D import (`Axes3D`) and draws a
  simple 3D curve.

Key checks:

```bash
(sionna-gpu) python3 check_matplotlib_3d.py
Matplotlib version: 3.10.7
Loaded from: /home/ryan/sionna-gpu/lib/python3.12/site-packages/matplotlib/__init__.py
mpl_toolkits from: /home/ryan/sionna-gpu/lib/python3.12/site-packages/mpl_toolkits/__init__.py
Axes3D import OK
```

If this script runs and shows a 3D plot window, your venv has a clean, venv‑local
Matplotlib installation with 3D support.

---

## 8. End‑to‑end Sionna unit driver (LDPC + 16‑QAM + AWGN + BER)

The main “does everything work?” script is:

* **`sionna_e2e_ldpc_awgn.py`**

What it does:

1. Configures TensorFlow to use GPU 0 with memory growth.

2. Prints environment info (TF/Sionna versions, GPU list).

3. Builds a simple link‑level chain:

   * `BinarySource` → random bits
   * `LDPC5GEncoder` → 5G LDPC code (k=512, n=1024, rate≈0.5)
   * `Mapper` / `Demapper` → 16‑QAM (`Constellation("qam", num_bits_per_symbol=4)`)
   * Manual complex AWGN layer driven by `ebnodb2no`
   * `LDPC5GDecoder` (hard output)

4. Optionally plots the 16‑QAM constellation in 3D (using Matplotlib Axes3D).

5. Runs a small BER sweep over Eb/N0 ∈ {0,2,4,6,8} dB on the GB10 and prints the
   measured BER on the **code bits**.

Example run:

```bash
(sionna-gpu) export TF_CPP_MIN_LOG_LEVEL=2   # optional: reduce TF verbosity
(sionna-gpu) python3 sionna_e2e_ldpc_awgn.py
=== Environment ===
TensorFlow: 2.17.0
Sionna    : 1.2.1
GPUs      : [PhysicalDevice(name='/physical_device:GPU:0', device_type='GPU')]

Using LDPC5G with k=512, n=1024, rate=0.500, M=2^4 (16-QAM)

Plotting 3D constellation (close the window to continue)...

Running BER sweep (this will use the GB10)...
Eb/N0 =  0.0 dB : BER(code bits) = 1.991e-01
Eb/N0 =  2.0 dB : BER(code bits) = 1.202e-01
Eb/N0 =  4.0 dB : BER(code bits) = 3.769e-04
Eb/N0 =  6.0 dB : BER(code bits) = 0.000e+00
Eb/N0 =  8.0 dB : BER(code bits) = 0.000e+00
```

This confirms:

* The Sionna PHY stack runs **end‑to‑end** on the GB10.
* CUDA kernels compile and execute despite some noisy warnings (see below).
* Matplotlib 3D plotting works in the same environment.

---

## 9. Noisy but harmless warnings

You will still see some warnings; they are noisy but not fatal.

### 9.1 cuFFT / cuDNN / cuBLAS “factory already registered”

At first import:

```text
E xla/stream_executor/cuda/cuda_fft.cc:485] Unable to register cuFFT factory...
E xla/stream_executor/cuda/cuda_dnn.cc:8473] Unable to register cuDNN factory...
E xla/stream_executor/cuda/cuda_blas.cc:1471] Unable to register cuBLAS factory...
```

These stem from duplicated factory registration in TF’s XLA backend on this
particular stack. They do **not** prevent GPU execution; the E2E unit test runs
fine.

You can soften TF log noise with:

```bash
export TF_CPP_MIN_LOG_LEVEL=2
```

but it won’t silence everything.

### 9.2 `'ptx85' is not a recognized feature for this target (ignoring feature)`

During the BER loop you’ll see many lines like:

```text
'+ptx85' is not a recognized feature for this target (ignoring feature)
```

These come from the underlying compiler toolchain emitting PTX feature flags
that don’t mean anything for the GB10’s architecture yet. They are warnings
only; kernels still compile and execute, as evidenced by the successful BER
sweep.

### 9.3 TensorRT dynamic library warnings

You may see:

```text
TF-TRT Warning: Could not find TensorRT: ...
Could not load dynamic library 'libnvinfer.so.10.8.0'
```

This just means TensorFlow’s TensorRT integration won’t be used; core CUDA
functionality (cuDNN, cuBLAS, etc.) works fine. The Sionna tests here don’t
depend on TensorRT.

---

## 10. Sionna components installed

Given the `--no-deps` Sionna install and the missing `mitsuba` wheel on
aarch64:

* **Installed and working:**

  * Sionna PHY and SYS layers (as Python package `sionna==1.2.1`).
  * LDPC5G encoder/decoder, modulation/mapping, AWGN, etc.
* **Not installed in this recipe:**

  * **Sionna‑RT (`sionna-rt`)** – the ray‑tracing / geometry engine, which
    depends on `mitsuba==3.7.1` (no aarch64 wheel as of Nov 2025).

If you only need link‑level / PHY‑layer simulations (LDPC, OFDM, MU‑MIMO, etc.)
this setup is sufficient. For RT features you’ll need either:

* an x86_64 host with official Sionna + Sionna‑RT support, or
* to manually build Mitsuba and Sionna‑RT from source for aarch64 (not covered
  here).

---

## 11. Files in this directory

* `check_tensorflow.py`
  Short TF sanity check: shows TF version, CUDA build flag and GPU devices.

* `inspect_tensorflow.py`
  Dumps TF build info (CUDA / cuDNN / TensorRT versions, supported SMs) and
  local devices; confirms that `nvidia-tensorflow` is a CUDA+TensorRT build
  with GB10 support.

* `check_sionna.py`
  Verifies Sionna, SciPy, Matplotlib versions, checks TF + GPU, and
  instantiates a 16‑QAM constellation to make sure Sionna’s mapping APIs work.

* `check_matplotlib_3d.py`
  Ensures Matplotlib is imported from the venv, that `mpl_toolkits.mplot3d`
  (Axes3D) loads correctly, and draws a simple 3D helix plot.

* `sionna_e2e_ldpc_awgn.py` 
  End‑to‑end chain:

  ```text
  bits → LDPC5G encode → 16‑QAM mapper → AWGN (manual) →
  demapper (LLRs) → LDPC5G decode → BER vs Eb/N0
  ```

  Also produces a 3D constellation plot using Matplotlib/Axes3D. 

---

## 12. Re‑creating this environment from scratch

Putting it all together:

```bash
# 0) Create and activate venv (no system site‑packages)
python3 -m venv ~/sionna-gpu
source ~/sionna-gpu/bin/activate
pip install --upgrade pip

# 1) Install GB10‑enabled TensorFlow from NGC
pip install "nvidia-tensorflow[horovod]" \
    --extra-index-url=https://pypi.ngc.nvidia.com/

# 2) Install Sionna PHY/SYS without touching TensorFlow
pip install "sionna==1.2.1" --no-deps

# 3) Install required numerical + plotting deps
pip install "scipy>=1.14.1" "matplotlib>=3.10" "importlib_resources>=6.4.5"
pip install pillow
pip install \
    "contourpy>=1.0.1" \
    "cycler>=0.10" \
    "fonttools>=4.22.0" \
    "pyparsing>=3" \
    "python-dateutil>=2.7"

# 4) Optional: reduce TF log noise
export TF_CPP_MIN_LOG_LEVEL=2

# 5) Run sanity checks and the E2E unit test
python3 check_tensorflow.py
python3 check_sionna.py
python3 check_matplotlib_3d.py
python3 sionna_e2e_ldpc_awgn.py
```

If all scripts run and the BER curve looks reasonable, you’ve reproduced the
working Sionna‑on‑DGX‑Spark stack described here.
