# LDPC Spike Study (COTS Focused Ablation)

This directory contains the focused **COTS spike ablation** used to investigate the temporary throughput peak observed near  
`N_cw ≈ 1024` in the full LDPC5G batch-scaling sweep.

The study was conducted on a **COTS workstation platform**:

- CPU: Intel **i9-14900K**
- GPU: NVIDIA **RTX 4090**
- Memory: DDR5 system RAM + discrete GPU VRAM
- Interconnect: **PCIe Gen4 x16**

The goal of this experiment is **not to produce the primary paper results**, but to explain the scaling behavior observed in the full sweep.

Specifically, the focused study tests whether the local maximum near `N_cw ≈ 1024` is caused by:

- PCIe bandwidth limits  
- GPU memory/workspace behavior  
- TensorFlow runtime / host orchestration effects  
- kernel occupancy transitions  

The results of this study appear in **Table I and Section V of the paper**.

---

# Experimental Design

The spike ablation profiles three batch sizes surrounding the observed maximum:

```

N_cw ∈ {512, 1024, 2048}

```

Each batch size is evaluated across three LDPC iteration counts:

```

I ∈ {4, 10, 20}

```

These points were selected because they span:

- **GPU ramp-up region**
- **observed local maximum**
- **dense regime transition**

Each configuration records **two outer trials**, each containing **10 decode repetitions**, matching the methodology used in the full study.

---

# Metrics Collected

During each run, the profiler records:

### GPU metrics

From `nvidia-smi`:

- GPU utilization
- memory utilization
- power draw
- performance state (P-state)
- clock rates

### PCIe metrics

To detect host-device bottlenecks:

- PCIe Rx / Tx bandwidth
- cumulative PCIe counters
- link generation
- link width

Commands used:

```

nvidia-smi dmon -s t
nvidia-smi pci -gCnt
lspci -vv

```

### CPU metrics

To capture runtime overhead:

- process CPU utilization
- system-wide CPU utilization
- active core equivalents

Commands used:

```

pidstat
mpstat
vmstat

```

### Runtime instrumentation

TensorFlow device placement logs were enabled to determine whether the decode graph executes purely on GPU or across both CPU and GPU.

---

# Key Finding

Across **19 focused runs**, the following observations were consistent:

1. The local maximum near `N_cw ≈ 1024` is **real and reproducible**.

2. The drop in throughput beyond `N_cw = 1024` **is not caused by PCIe saturation**.

   Observed PCIe traffic remained:

```

tens to low hundreds of MB/s

```

while the GPU link remained:

```

PCIe Gen4 x16 current=max

```

3. TensorFlow placement logs and telemetry show the decode path is a **hybrid CPU+GPU runtime**.

4. In the hottest runs the benchmark consumed:

```

~27–29 active CPU cores

```

indicating substantial host-side orchestration.

5. The most supported interpretation is therefore:

```

a medium-batch compute/locality sweet spot near N_cw ≈ 1024

```

where GPU occupancy is high while decoder workspace and runtime overhead remain favorable.

At larger batch sizes (`N_cw ≥ 2048`), the implementation transitions to a **lower-efficiency dense regime** driven by larger decoder working sets and runtime overhead.

---

# Why the Effect is Smaller on DGX Spark

The spike is significantly less pronounced on **DGX Spark** because:

```

CPU ↔ GPU memory is coherent (NVLink-C2C)

```

This removes the discrete host/device boundary present on the COTS system and reduces sensitivity to runtime placement and memory movement effects.

---

# Running the Spike Study

From the `ldpc_spike` directory:

```

./profile_ldpc_spike_cots.sh 
--bench ../ldpc_cpu_gpu_benchmark.py 
--iters 4,10,20 
--outer-reps 2 
--inner-repeat 10

```

This will execute the focused profiling sweep and generate per-run logs containing:

```

benchmark.txt
gpu_metrics.csv
pcie_dmon.txt
pcie_gcnt.txt
pidstat.txt
mpstat.txt
vmstat.txt
nvidia_smi_q.txt

```

---

# Relationship to the Main Benchmark

The primary experiment in this repository is the **full LDPC scaling sweep** located in:

```

six-times-to-spare/i9-14900K-rtx-4090/

```

which evaluates:

```

N_cw = 1 … 20480
I = 4 … 22

```

The spike study is a **diagnostic follow-up** used to explain the behavior observed in that sweep.

---

# Paper Reference

Results from this directory are summarized in:

```

Table I – Focused COTS Spike Ablation
Section V – Results and Evaluation

```

of the paper:

```

Six Times to Spare: Characterizing GPU-Accelerated 5G LDPC Decoding for Edge-RSU Communications

```

