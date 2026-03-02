#!/usr/bin/env bash
set -euo pipefail

CSV="ldpc_sionna_spark.csv"
CHECKPOINT="ldpc_sionna_spark.checkpoint"

# 10 values of num_codewords (nice spread, all multiples of 2048)
NUM_CODEWORDS_VALUES=(
  2048 4096 6144 8192 10240 12288 14336 16384 18432 20480
)

# 10 values of num_iter (more granular than 5/10/20)
NUM_ITER_VALUES=(
  4 6 8 10 12 14 16 18 20 22
)

# 10 repetitions per (N, I) pair -> 10 * 10 * 10 = 1000 rows
REPS=10

# Globals used for skip logic
LAST_REP=0
LAST_N=0
LAST_I=0

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
