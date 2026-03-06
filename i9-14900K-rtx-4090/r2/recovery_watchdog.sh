#!/usr/bin/env bash
set -u

SCRIPT="./sweep_ldpc_cumulative.sh"
LOG="./sweep_ldpc_cumulative.watchdog.log"
PIDFILE="./sweep_ldpc_cumulative.pid"

SESSION="ldpc_sweep"
WINDOW="sweep"

# Supervisor behavior
CHECK_INTERVAL=5          # seconds between health checks
RESTART_BACKOFF=10        # extra delay after a crash before restart
ATTACH_ON_START=0         # set to 1 only if you explicitly want auto-attach

SCRIPT_ABS="$(cd "$(dirname "$SCRIPT")" && pwd)/$(basename "$SCRIPT")"
SCRIPT_DIR="$(dirname "$SCRIPT_ABS")"

timestamp() { date +"%Y-%m-%d %H:%M:%S"; }

log() {
  local level="$1"
  shift
  printf '[%s] %s: %s\n' "$(timestamp)" "$level" "$*" | tee -a "$LOG"
}

tmux_available() {
  command -v tmux >/dev/null 2>&1
}

require_prereqs() {
  if [[ ! -x "$SCRIPT" ]]; then
    log "ERROR" "$SCRIPT not found or not executable"
    exit 1
  fi

  if ! tmux_available; then
    log "ERROR" "tmux is not installed"
    exit 1
  fi
}

window_exists() {
  tmux list-windows -t "$SESSION" -F "#{window_name}" 2>/dev/null | grep -Fxq "$WINDOW"
}

pane_dead() {
  local dead
  dead="$(tmux display-message -p -t "${SESSION}:${WINDOW}" "#{pane_dead}" 2>/dev/null || echo 1)"
  [[ "$dead" == "1" ]]
}

pane_pid() {
  tmux display-message -p -t "${SESSION}:${WINDOW}" "#{pane_pid}" 2>/dev/null || true
}

pane_cmd() {
  tmux display-message -p -t "${SESSION}:${WINDOW}" "#{pane_current_command}" 2>/dev/null || true
}

build_run_cmd() {
  cat <<EOF
cd "${SCRIPT_DIR}" && \
source "${HOME}/sionna-gpu/bin/activate" && \
echo "[$(timestamp)] RUN: ${SCRIPT_ABS} (venv: sionna-gpu)" | tee -a "${LOG}" && \
exec "${SCRIPT_ABS}" 2>&1 | tee -a "${LOG}"
EOF
}

start_or_respawn_window() {
  local run_cmd
  run_cmd="$(build_run_cmd)"

  tmux start-server

  if tmux has-session -t "$SESSION" 2>/dev/null; then
    if window_exists; then
      log "INFO" "respawning tmux window '${SESSION}:${WINDOW}'"
      tmux respawn-window -k -t "${SESSION}:${WINDOW}" "bash -lc '$run_cmd'"
    else
      log "INFO" "creating tmux window '${SESSION}:${WINDOW}'"
      tmux new-window -t "$SESSION" -n "$WINDOW" "bash -lc '$run_cmd'"
    fi
  else
    log "INFO" "creating tmux session '${SESSION}', window '${WINDOW}'"
    tmux new-session -d -s "$SESSION" -n "$WINDOW" "bash -lc '$run_cmd'"
  fi

  local pid
  pid="$(pane_pid)"
  if [[ -n "$pid" ]]; then
    echo "$pid" > "$PIDFILE"
  fi
}

attach_tmux() {
  if [[ -t 1 ]]; then
    if [[ -n "${TMUX:-}" ]]; then
      tmux switch-client -t "${SESSION}:${WINDOW}" 2>/dev/null || tmux switch-client -t "${SESSION}"
    else
      tmux attach -t "${SESSION}:${WINDOW}" 2>/dev/null || tmux attach -t "${SESSION}"
    fi
  else
    log "INFO" "no TTY detected; skipping attach"
  fi
}

supervise_forever() {
  local first_start=1

  while true; do
    tmux start-server

    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
      log "WARN" "tmux session '${SESSION}' not found; starting sweep"
      start_or_respawn_window

      if (( first_start == 1 )) && (( ATTACH_ON_START == 1 )); then
        first_start=0
        attach_tmux
      else
        first_start=0
      fi

      sleep "$CHECK_INTERVAL"
      continue
    fi

    if ! window_exists; then
      log "WARN" "tmux window '${SESSION}:${WINDOW}' not found; recreating"
      start_or_respawn_window
      sleep "$CHECK_INTERVAL"
      continue
    fi

    if pane_dead; then
      local dead_status
      dead_status="$(tmux display-message -p -t "${SESSION}:${WINDOW}" "#{pane_dead_status}" 2>/dev/null || echo "unknown")"
      log "ERROR" "tmux pane is dead (exit status: ${dead_status}); restarting after ${RESTART_BACKOFF}s backoff"
      sleep "$RESTART_BACKOFF"
      start_or_respawn_window
      sleep "$CHECK_INTERVAL"
      continue
    fi

    local pid cmd
    pid="$(pane_pid)"
    cmd="$(pane_cmd)"

    if [[ -n "$pid" ]]; then
      echo "$pid" > "$PIDFILE"
    fi

    log "OK" "supervising '${SESSION}:${WINDOW}' (pane_pid=${pid:-unknown}, cmd=${cmd:-unknown})"
    sleep "$CHECK_INTERVAL"
  done
}

main() {
  require_prereqs
  log "INFO" "watchdog starting for ${SCRIPT_ABS}"
  log "INFO" "tmux target: session='${SESSION}', window='${WINDOW}'"
  log "INFO" "check interval=${CHECK_INTERVAL}s, restart backoff=${RESTART_BACKOFF}s"
  supervise_forever
}

main "$@"
