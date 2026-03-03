# NVIDIA DGX Spark

A Grace Blackwell AI supercomputer on your desk.

This document collects key links, a concise hardware summary, and notes on power behavior for the NVIDIA DGX™ Spark.

---

## Official Resources

- **Landing page:**
  https://www.nvidia.com/en-us/products/workstations/dgx-spark/
- **Datasheet (PDF):**
  https://nvdam.widen.net/s/tlzm8smqjx/workstation-datasheet-dgx-spark-gtc25-spring-nvidia-us-3716899-web

---

## Hardware Overview (from datasheet)

**Platform**
- Architecture: **NVIDIA Grace Blackwell** (GB10 Superchip) 
- GPU: **NVIDIA Blackwell** architecture GPU with 5th-gen Tensor Cores (FP4 support), up to **1 PFLOP AI** (theoretical FP4 with sparsity) 
- CPU: **20-core Arm Grace CPU** (10× Cortex-X925 + 10× Cortex-A725) 
- Coherent CPU ↔ GPU memory via **NVLink-C2C**, with significantly higher bandwidth than PCIe Gen5.

**Memory & Storage**
- **128 GB** LPDDR5x **coherent unified system memory** 
- **4 TB** NVMe M.2 SSD with self-encryption

**Networking & I/O**
- 1× **ConnectX-7** NIC @ **200 Gbps** (for Spark ↔ Spark link, up to 405B-parameter models) 
- 1× **10 GbE RJ-45** 
- **Wi-Fi 7** and **Bluetooth 5.4 (LE)** 
- 4× **USB-C** ports 
- 1× **HDMI 2.1a** display output with multichannel audio

**Form Factor & Power**
- Compact desktop chassis: **150 mm (L) × 150 mm (W) × 50.5 mm (H)** 
- Weight: **1.2 kg** 
- **System power supply:** 240 W 
- **GB10 TDP (CPU+GPU):** 140 W 

**OS Reflash**
https://docs.nvidia.com/dgx/dgx-spark/system-recovery.html

**Workload Envelope (high level)**
- Prototype, fine-tune, and inference **large language models up to ~200B parameters** on a single DGX Spark (FP4) 
- Connect two DGX Sparks via ConnectX-7 for models up to **405B parameters** (e.g., Llama-3.1-405B scale) 

---

## Power Characteristics

DGX Spark’s **peak total system power is 240 W**.
- The **TDP of the GB10 SoC** (includes both GPU and CPU) is **140 W**. 
- The remaining **~100 W** budget covers **ConnectX-7, SSD, and USB-C peripherals**. 
- The datasheet and NVIDIA product webpage have been updated to reflect these values.

> **Important:** When measuring power usage via `nvidia-smi`, the reported wattage reflects **GPU power only**, not total system draw.

---

## Typical Use Cases (Summary)

DGX Spark is designed as a **desktop AI development node** that mirrors NVIDIA’s data center AI stack:

- **Prototyping:** 
  Build, test, and validate AI models and AI-augmented applications locally, then promote workloads to DGX Cloud or other NVIDIA-accelerated infrastructure.
- **Fine-tuning:** 
  Fine-tune pre-trained models (up to ~70B parameters) within the 128 GB unified memory footprint.
- **Inference at scale:** 
  Run inference for models up to ~200B parameters on a single unit, leveraging FP4 Tensor Cores for high throughput.
- **Data science & analytics:** 
  Accelerate large, compute-intensive analytics and classical ML workflows with 1 PFLOP of parallel compute and large unified memory.
- **Edge & robotics development:** 
  Develop and test applications using NVIDIA frameworks such as **Isaac™, Metropolis, and Holoscan** for robotics, smart cities, computer vision, and other edge workloads.

---

## Software Stack (High Level)

DGX Spark ships with:

- **NVIDIA DGX OS** (Ubuntu-based) 
- **NVIDIA AI software stack** preconfigured (CUDA, CUDA-X libraries, drivers, container runtime) 
- Support for common tools and frameworks (e.g., **PyTorch, TensorFlow, Jupyter, Ollama**)
- Access to **NVIDIA NIM™**, **Blueprints**, and other NVIDIA developer resources for rapid onboarding 

---

## OS Reflash (DGX OS – Custom Ubuntu 24.04 LTS Variant)
If an OS-level installation (e.g., Aerial Omniverse Digital Twin, custom CUDA stacks, or a manual Ubuntu overwrite) corrupts the DGX OS, you can fully restore the factory **DGX OS 1.x** image — NVIDIA’s customized Ubuntu **24.04 LTS deviant** with preinstalled drivers, firmware, NVLink-C2C support, and DGX management services.

**Recovery Guide:** 
[https://docs.nvidia.com/dgx/dgx-spark/system-recovery.html](https://docs.nvidia.com/dgx/dgx-spark/system-recovery.html)

### Quick 4-Bullet Reflash Procedure
- **1. Download NVIDIA’s official DGX Spark recovery image** 
  Retrieve the DGX Spark Founders Edition recovery bundle ( `.tar.gz` ) from NVIDIA support. This contains the *exact* factory DGX OS used at shipment — not stock Ubuntu — including Grace–Blackwell firmware, NVIDIA-validated kernel, and system profiles.
- **2. Create a bootable recovery USB (16 GB+)** 
  Extract the archive and run the platform-specific script: 
  `CreateUSBKey.sh` (Linux), `CreateUSBKey.cmd` (Windows), or `CreateUSBKeyMacOS.sh` (macOS). 
  *This wipes the USB drive and writes the official DGX recovery environment.*
- **3. Boot into UEFI and enable recovery mode** 
  Power on while holding **Del**, restore UEFI defaults, confirm **Secure Boot = Enabled**, restore factory keys, then use **Boot Override** to select the USB drive. 
  The system will reboot into the NVIDIA recovery tool.
- **4. Reflash the internal SSD to factory state** 
  On the recovery screen, select **START RECOVERY** to erase and reinstall the DGX OS (Ubuntu 24.04 LTS variant) along with all firmware and configuration defaults. 
  After completion, reboot normally — your DGX Spark returns to its original, fully supported factory software image.

---

## How DGX Spark Compares to GH200 / GB200 Edge-Class Servers

### Architectural Positioning

NVIDIA DGX Spark sits at the *workstation / edge* end of the Grace–Blackwell family:

- **DGX Spark (GB10)** 
  - 20-core Grace CPU (Arm) + integrated Blackwell GPU in a single low-power SoC. 
  - **128 GB unified LPDDR5x** system memory shared coherently between CPU and GPU.
  - Up to **1 PFLOP FP4** (sparse) AI performance in a **240 W** desktop form factor.
- **GH200 Grace Hopper servers** 
  - 72-core Grace CPU + Hopper GPU (H100/H200-class) on a superchip.
  - Hundreds of GB of **LPDDR5x** on Grace + **HBM3/HBM3e** on the GPU (up to ~480 GB CPU RAM + 96–144 GB HBM). 
  - Node power in the **hundreds of watts up to ~1 kW**, designed for data-center racks rather than desks. 
- **GB200 / GB300 rack-scale systems (e.g., NVL72)** 
  - Multi-GPU Grace Blackwell superchips (2× B200 + 1× Grace per GB200) interconnected via 5th-gen NVLink. 
  - **Tens to hundreds of PFLOPs FP8/FP4** per rack for training and real-time inference of trillion-parameter models.
  - Liquid-cooled, rack-scale “AI factory” systems—orders of magnitude more compute, memory, and power draw than Spark.

In short:
- **DGX Spark (GB10)**: single, low-power Grace–Blackwell SoC + 128 GB unified RAM. 
- **GH200/GB200**: much larger, HBM-backed accelerators with far more FLOPS, memory bandwidth, and scale—but also much higher power, cost, and operational overhead.

### What Workloads DGX Spark Is Optimized For

DGX Spark is not trying to be a miniature GB200 rack. It’s optimized for **developer-centric edge and desktop AI**:
- **Edge / on-prem inference and prototyping**
  - 128 GB of coherent shared memory lets you host **very large parameter counts** (up to ~200B in FP4) without the usual CPU ↔ GPU copy overhead.
  - Ideal for **serving and iterating on large models locally** where data can’t or shouldn’t leave the edge site.
- **Multi-agent and multimodal systems**
  - The unified RAM + moderate GPU makes Spark **excellent at running many models in parallel** (LLMs, vision encoders, speech models, tool-using agents) rather than just one giant model as fast as possible.
  - Think: **agentic workflows, orchestration layers, and tool-chains** where dozens of smaller or mid-size models collaborate, share context, and stream data through a common memory space.
- **Developer desktop for GB200 / cloud backends**
  - Spark is a **“front-end lab bench”**: you prototype prompts, pipelines, and agents locally, then scale successful workloads to GH200/GB200-based clusters (DGX Cloud, on-prem AI factories) for massive throughput.
  - Great fit for **fine-tuning up to ~70B** and **profiling/integration** tasks before pushing to bigger hardware.
- **Data science and classical ML**
  - 1 PFLOP FP4 plus 128 GB unified memory is more than enough for a broad range of **tabular, time-series, and analytics workloads**, especially when models and datasets need to coexist in memory.

### Per-Model Latency vs. Concurrency

A key design trade-off:
- **Per-model inference time (single large model)** 
  - High-end accelerators like **H100, B100/B200, or GH200/GB200 nodes** have far more raw FLOPS, HBM bandwidth, and scaling options. 
  - For the *same* model and batch size, **per-query latency will generally be lower** on those larger GPUs than on GB10—especially for very large LLMs or vision transformers with heavy attention blocks.
- **Concurrency and system-level throughput**
  - DGX Spark’s strength is **concurrency at the edge**:
    - Many models in memory at once (LLMs, embedding models, rerankers, vision/speech, tools). 
    - Many concurrent sessions / agents per node, without constantly swapping weights in and out of limited VRAM.
  - If your workload is: 
    > “Run a *lot* of medium/large models, agents, and tools together in a 240 W box, close to the data,” then **Spark shines**.

### When to Use Spark vs. GH200 / GB200
- **Choose DGX Spark when:**
  - You want **desktop or edge inference**, prototyping, and multi-agent experimentation. 
  - You care about **power and noise budgets** (lab, office, or edge closet) and can’t host a full data-center node. 
  - You’re building **multi-model systems**, RAG pipelines, or agent stacks where memory coherence and concurrency matter more than absolute single-model FLOPS.
- **Step up to GH200 / GB200 when:**
  - You need to **train or fine-tune very large models at scale** (hundreds of billions to trillions of parameters). 
  - You require **lowest possible latency** for a single massive model or very high QPS at cloud scale. 
  - You’re operating an “AI factory” where rack-scale NVLink domains and multi-rack clusters are justified.

In other words: **DGX Spark is the edge-class “control plane” and prototyping node for your AI stack**, while **GH200/GB200-class systems are the heavy-duty “data plane” for large-scale training and hyperscale inference.**
