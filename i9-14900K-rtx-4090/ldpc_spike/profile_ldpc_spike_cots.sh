#!/usr/bin/env bash
set -euo pipefail

# Focused profiler for the RTX 4090 spike region in the LDPC benchmark.
# Calls the existing ldpc_cpu_gpu_benchmark.py driver and captures:
#   - PCIe Rx/Tx throughput
#   - current/max PCIe link gen + width
#   - GPU util + memory util
#   - pstate / SM clocks / MEM clocks / power / temp
#   - TensorFlow device placement logs
#   - optional process/system CPU stats
#
# Default focus region:
#   N_cw in {512, 1024, 2048}
#   num_iter in {10}
#
# Example:
#   ./profile_ldpc_spike_cots.sh
#   ./profile_ldpc_spike_cots.sh --iters 4,10,20 --outer-reps 3 --inner-repeat 10
#   ./profile_ldpc_spike_cots.sh --bench ./ldpc_cpu_gpu_benchmark.py --gpu-index 0

BENCH_PY="./ldpc_cpu_gpu_benchmark.py"
GPU_INDEX=0
OUT_ROOT="ldpc_spike_profile_$(date +%Y%m%d_%H%M%S)"
CSV_SUMMARY="ldpc_spike_profile_summary.csv"
INNER_REPEAT=10
OUTER_REPS=2
NUM_CODEWORDS_CSV="512,1024,2048"
NUM_ITERS_CSV="10"
CPU_THREADS=""
EBNO_DB="4.0"
LABEL_PREFIX="spike_probe"
ENABLE_CPU_RUN=0

usage() {
  cat <<USAGE
Usage: $0 [options]

Options:
  --bench PATH            Path to ldpc_cpu_gpu_benchmark.py (default: ${BENCH_PY})
  --gpu-index IDX         GPU index for nvidia-smi monitoring (default: ${GPU_INDEX})
  --out-root DIR          Output root directory (default: ${OUT_ROOT})
  --csv-path PATH         Summary CSV written by the benchmark driver (default: ${CSV_SUMMARY})
  --num-codewords LIST    Comma-separated N_cw values (default: ${NUM_CODEWORDS_CSV})
  --iters LIST            Comma-separated num_iter values (default: ${NUM_ITERS_CSV})
  --outer-reps N          Number of outer repeated runs per point (default: ${OUTER_REPS})
  --inner-repeat N        Benchmark --repeat value passed to driver (default: ${INNER_REPEAT})
  --ebno-db X             Benchmark Eb/N0 in dB (default: ${EBNO_DB})
  --cpu-threads N         Optional --cpu-threads value passed to driver
  --label-prefix STR      Prefix for run labels (default: ${LABEL_PREFIX})
  --enable-cpu-run        Also run the CPU path inside the driver (default: GPU only)
  -h, --help              Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bench) BENCH_PY="$2"; shift 2 ;;
    --gpu-index) GPU_INDEX="$2"; shift 2 ;;
    --out-root) OUT_ROOT="$2"; shift 2 ;;
    --csv-path) CSV_SUMMARY="$2"; shift 2 ;;
    --num-codewords) NUM_CODEWORDS_CSV="$2"; shift 2 ;;
    --iters) NUM_ITERS_CSV="$2"; shift 2 ;;
    --outer-reps) OUTER_REPS="$2"; shift 2 ;;
    --inner-repeat) INNER_REPEAT="$2"; shift 2 ;;
    --ebno-db) EBNO_DB="$2"; shift 2 ;;
    --cpu-threads) CPU_THREADS="$2"; shift 2 ;;
    --label-prefix) LABEL_PREFIX="$2"; shift 2 ;;
    --enable-cpu-run) ENABLE_CPU_RUN=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ ! -f "$BENCH_PY" ]]; then
  echo "Benchmark driver not found: $BENCH_PY" >&2
  exit 1
fi

mkdir -p "$OUT_ROOT"

# split comma-separated lists into arrays
IFS=',' read -r -a NUM_CODEWORDS_VALUES <<< "$NUM_CODEWORDS_CSV"
IFS=',' read -r -a NUM_ITER_VALUES <<< "$NUM_ITERS_CSV"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

require_cmd python3
require_cmd nvidia-smi

PIDSTAT_AVAILABLE=1
MPSTAT_AVAILABLE=1
VMSTAT_AVAILABLE=1
LSPCI_AVAILABLE=1
command -v pidstat >/dev/null 2>&1 || PIDSTAT_AVAILABLE=0
command -v mpstat  >/dev/null 2>&1 || MPSTAT_AVAILABLE=0
command -v vmstat  >/dev/null 2>&1 || VMSTAT_AVAILABLE=0
command -v lspci   >/dev/null 2>&1 || LSPCI_AVAILABLE=0

GPU_BUS_ID="$(nvidia-smi --query-gpu=pci.bus_id --format=csv,noheader -i "$GPU_INDEX" | head -n1 | tr -d '[:space:]')"
GPU_UUID="$(nvidia-smi --query-gpu=uuid --format=csv,noheader -i "$GPU_INDEX" | head -n1 | tr -d '[:space:]')"

echo "Output root      : $OUT_ROOT"
echo "Benchmark driver : $BENCH_PY"
echo "GPU index        : $GPU_INDEX"
echo "GPU bus id       : $GPU_BUS_ID"
echo "GPU uuid         : $GPU_UUID"
echo "N_cw values      : ${NUM_CODEWORDS_VALUES[*]}"
echo "num_iter values  : ${NUM_ITER_VALUES[*]}"
echo "outer reps       : $OUTER_REPS"
echo "inner repeat     : $INNER_REPEAT"
echo

write_static_metadata() {
  local run_dir="$1"
  {
    echo "timestamp=$(date --iso-8601=seconds)"
    echo "hostname=$(hostname)"
    echo "kernel=$(uname -a)"
    echo "gpu_index=$GPU_INDEX"
    echo "gpu_bus_id=$GPU_BUS_ID"
    echo "gpu_uuid=$GPU_UUID"
    echo "bench_py=$BENCH_PY"
    echo "ebno_db=$EBNO_DB"
    echo "inner_repeat=$INNER_REPEAT"
  } > "$run_dir/run_meta.env"

  nvidia-smi -L > "$run_dir/nvidia_smi_L.txt"
  nvidia-smi -i "$GPU_INDEX" -q -d CLOCK,PERFORMANCE,UTILIZATION,MEMORY,POWER > "$run_dir/nvidia_smi_q.txt" || true

  if [[ "$LSPCI_AVAILABLE" -eq 1 ]]; then
    lspci -tv > "$run_dir/lspci_tree.txt" || true
    lspci -s "${GPU_BUS_ID#0000:}" -vv > "$run_dir/lspci_gpu_vv.txt" || true
  fi
}

start_monitors() {
  local run_dir="$1"
  local bench_pid="$2"

  # Fast GPU metrics sampler
  nvidia-smi -i "$GPU_INDEX" \
    --query-gpu=timestamp,index,name,pstate,power.draw,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu,utilization.memory,memory.used,memory.total,pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current,pcie.link.width.max \
    --format=csv -lms 200 > "$run_dir/gpu_metrics.csv" 2> "$run_dir/gpu_metrics.err" &
  MON_GPU_QUERY_PID=$!

  # PCIe RX/TX throughput monitor
  nvidia-smi dmon -i "$GPU_INDEX" -s t -d 1 -o DT > "$run_dir/pcie_dmon.txt" 2> "$run_dir/pcie_dmon.err" &
  MON_PCIE_DMON_PID=$!

  # PCIe counter snapshots once per second
  (
    while true; do
      echo "===== $(date --iso-8601=seconds) ====="
      nvidia-smi pci -i "$GPU_INDEX" -gCnt
      sleep 1
    done
  ) > "$run_dir/pcie_gcnt.txt" 2> "$run_dir/pcie_gcnt.err" &
  MON_PCIE_GCNT_PID=$!

  # Link-state snapshots once per second (under load)
  (
    while true; do
      echo "===== $(date --iso-8601=seconds) ====="
      nvidia-smi -i "$GPU_INDEX" --query-gpu=index,name,pci.bus_id,pstate,pcie.link.gen.current,pcie.link.gen.max,pcie.link.width.current,pcie.link.width.max --format=csv
      sleep 1
    done
  ) > "$run_dir/pcie_link_state.txt" 2> "$run_dir/pcie_link_state.err" &
  MON_LINK_PID=$!

  # Optional benchmark PID stats
  if [[ "$PIDSTAT_AVAILABLE" -eq 1 ]]; then
    pidstat -urd -h -p "$bench_pid" 1 > "$run_dir/pidstat.txt" 2> "$run_dir/pidstat.err" &
    MON_PIDSTAT_PID=$!
  else
    MON_PIDSTAT_PID=""
  fi

  if [[ "$MPSTAT_AVAILABLE" -eq 1 ]]; then
    mpstat -P ALL 1 > "$run_dir/mpstat.txt" 2> "$run_dir/mpstat.err" &
    MON_MPSTAT_PID=$!
  else
    MON_MPSTAT_PID=""
  fi

  if [[ "$VMSTAT_AVAILABLE" -eq 1 ]]; then
    vmstat 1 > "$run_dir/vmstat.txt" 2> "$run_dir/vmstat.err" &
    MON_VMSTAT_PID=$!
  else
    MON_VMSTAT_PID=""
  fi
}

stop_monitors() {
  local pids=(
    "${MON_GPU_QUERY_PID:-}"
    "${MON_PCIE_DMON_PID:-}"
    "${MON_PCIE_GCNT_PID:-}"
    "${MON_LINK_PID:-}"
    "${MON_PIDSTAT_PID:-}"
    "${MON_MPSTAT_PID:-}"
    "${MON_VMSTAT_PID:-}"
  )
  for pid in "${pids[@]}"; do
    if [[ -n "$pid" ]]; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
    fi
  done
}

cleanup() {
  stop_monitors || true
}
trap cleanup EXIT INT TERM

run_point() {
  local n_cw="$1"
  local n_iter="$2"
  local outer_rep="$3"

  local label="${LABEL_PREFIX}_N${n_cw}_I${n_iter}_r${outer_rep}"
  local run_dir="$OUT_ROOT/$label"
  mkdir -p "$run_dir"
  write_static_metadata "$run_dir"

  echo "============================================================"
  echo "Running $label"
  echo "  N_cw      : $n_cw"
  echo "  num_iter  : $n_iter"
  echo "  run dir   : $run_dir"
  echo "============================================================"

  local no_gpu_flag=""

  # Run benchmark in background so we can attach monitors to the benchmark PID.
  (
    exec python3 - "$BENCH_PY" "$n_cw" "$n_iter" "$INNER_REPEAT" "$CSV_SUMMARY" "$label" "$EBNO_DB" "$CPU_THREADS" "$no_gpu_flag" <<'PY'
import runpy
import sys
import tensorflow as tf

bench_py    = sys.argv[1]
num_cw      = sys.argv[2]
num_iter    = sys.argv[3]
inner_rep   = sys.argv[4]
csv_path    = sys.argv[5]
label       = sys.argv[6]
ebno_db     = sys.argv[7]
cpu_threads = sys.argv[8]
no_gpu_flag = sys.argv[9]

# Enable verbose placement logging to catch CPU fallbacks / transfers.
tf.debugging.set_log_device_placement(True)

argv = [
    bench_py,
    "--num-codewords", num_cw,
    "--num-iter", num_iter,
    "--repeat", inner_rep,
    "--csv-path", csv_path,
    "--label", label,
    "--ebno-db", ebno_db,
]
if cpu_threads:
    argv += ["--cpu-threads", cpu_threads]
if no_gpu_flag:
    argv += [no_gpu_flag]

sys.argv = argv
runpy.run_path(bench_py, run_name="__main__")
PY
  ) > "$run_dir/benchmark.txt" 2> "$run_dir/benchmark.err" &
  local bench_pid=$!

  # Give Python a moment to start before attaching PID-based monitors.
  sleep 1
  start_monitors "$run_dir" "$bench_pid"

  wait "$bench_pid"
  local rc=$?

  stop_monitors

  echo "$rc" > "$run_dir/exit_code.txt"
  if [[ "$rc" -ne 0 ]]; then
    echo "Run failed: $label (exit $rc)" >&2
    return "$rc"
  fi

  echo "Completed $label"
}

for outer_rep in $(seq 1 "$OUTER_REPS"); do
  for n_cw in "${NUM_CODEWORDS_VALUES[@]}"; do
    for n_iter in "${NUM_ITER_VALUES[@]}"; do
      run_point "$n_cw" "$n_iter" "$outer_rep"
    done
  done
done

echo
echo "All focused runs complete. Output root: $OUT_ROOT"
