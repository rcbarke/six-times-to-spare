#!/usr/bin/env bash
set -euo pipefail

CSV="ldpc_sionna_spark.csv"
CHECKPOINT="ldpc_sionna_spark.checkpoint"

# Monitor outputs (as requested)
GPU_MON_CSV="gpu_ldpc_sweep_stats.csv"
PIDSTAT_LOG="pid_ldpc_sweep_stats.log"

# Full 21 value range of num_codewords 
NUM_CODEWORDS_VALUES=(
  1 2 4 8 16 32 64 128 256 512 1024 2048 4096 6144 8192 10240 12288 14336 16384 18432 20480
)

# 10 values of num_iter (belief propagations)
NUM_ITER_VALUES=(
  4 6 8 10 12 14 16 18 20 22
)

# 10 repetitions per (N, I) pair -> 10 * 10 * 10 = 1000 rows
REPS=10

# Globals used for skip logic
LAST_REP=0
LAST_N=0
LAST_I=0

GPU_MON_PID=""
PIDSTAT_PID=""

cleanup() {
  # Best-effort cleanup; don't fail cleanup if something is already gone.
  set +e
  if [[ -n "${GPU_MON_PID}" ]]; then
    kill "${GPU_MON_PID}" 2>/dev/null
    wait "${GPU_MON_PID}" 2>/dev/null
  fi
  if [[ -n "${PIDSTAT_PID}" ]]; then
    kill "${PIDSTAT_PID}" 2>/dev/null
    wait "${PIDSTAT_PID}" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

start_monitors() {
  # Truncate outputs each fresh run (change to >> if you prefer appending)
  : > "${GPU_MON_CSV}"
  : > "${PIDSTAT_LOG}"

  # GPU monitor (1 Hz)
  # Note: nvidia-smi writes a CSV header; that's fine and helpful.
  nvidia-smi --query-gpu=timestamp,utilization.gpu,power.draw --format=csv -l 1 \
    > "${GPU_MON_CSV}" &
  GPU_MON_PID=$!
  echo "Started GPU monitor (PID=${GPU_MON_PID}) -> ${GPU_MON_CSV}"

  # CPU/process monitor (1 Hz)
  # pidstat typically needs sysstat installed.
  pidstat -u -p ALL 1 > "${PIDSTAT_LOG}" &
  PIDSTAT_PID=$!
  echo "Started pidstat monitor (PID=${PIDSTAT_PID}) -> ${PIDSTAT_LOG}"
}

load_checkpoint() {
  if [[ -f "${CHECKPOINT}" ]]; then
    echo "Loading checkpoint from ${CHECKPOINT}"
    # shellcheck source=/dev/null
    . "${CHECKPOINT}"
    echo "Last completed iteration: rep=${LAST_REP}, N=${LAST_N}, I=${LAST_I}"
  else
    echo "No checkpoint file found, starting from the very beginning."
  fi
}

write_checkpoint() {
  local rep="$1"
  local n="$2"
  local i="$3"

  cat > "${CHECKPOINT}" <<EOF
LAST_REP=${rep}
LAST_N=${n}
LAST_I=${i}
EOF
}

# Return 0 (true) if this (rep, N, I) should be skipped because it is
# <= the last completed triple in lexicographic order.
should_skip() {
  local rep="$1"
  local n="$2"
  local i="$3"

  # Anything in an earlier repetition is done
  if (( rep < LAST_REP )); then
    return 0
  elif (( rep > LAST_REP )); then
    return 1
  fi

  # Same repetition; compare N
  if (( n < LAST_N )); then
    return 0
  elif (( n > LAST_N )); then
    return 1
  fi

  # Same rep and same N; compare I
  if (( i <= LAST_I )); then
    return 0
  else
    return 1
  fi
}

load_checkpoint
start_monitors

for rep in $(seq 1 "${REPS}"); do
  echo "=== Repetition ${rep}/${REPS} ==="
  for N in "${NUM_CODEWORDS_VALUES[@]}"; do
    for I in "${NUM_ITER_VALUES[@]}"; do

      if should_skip "${rep}" "${N}" "${I}"; then
        # Already completed in a previous run; keep the sweep order, just don't rerun
        continue
      fi

      echo "Running: num_codewords=${N}, num_iter=${I}, rep=${rep}"
      python3 ldpc_cpu_gpu_benchmark.py \
        --num-codewords "${N}" \
        --num-iter "${I}" \
        --repeat 10 \
        --csv-path "${CSV}" \
        --label "rep${rep}_N${N}_I${I}"

      # Only reached if the python job succeeded (set -e), so it's safe to mark as done
      write_checkpoint "${rep}" "${N}" "${I}"
    done
  done
done

echo "Sweep complete. Final checkpoint: rep=${LAST_REP}, N=${LAST_N}, I=${LAST_I}"
