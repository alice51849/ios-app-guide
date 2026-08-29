#!/usr/bin/env bash

_BOUNDED_RETRY_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1
  pwd
)"

run_bounded_retry() {
  if [ "$#" -lt 5 ]; then
    echo \
      "run_bounded_retry requires: seconds attempts delay label command..." \
      >&2
    return 64
  fi

  local seconds="$1"
  local max_attempts="$2"
  local retry_delay="$3"
  local label="$4"
  shift 4

  if ! [[ "$seconds" =~ ^[0-9]+([.][0-9]+)?$ ]] \
    || ! [[ "$max_attempts" =~ ^[1-9][0-9]*$ ]] \
    || ! [[ "$retry_delay" =~ ^[0-9]+$ ]]; then
    echo "invalid bounded retry configuration for ${label}" >&2
    return 64
  fi

  local attempt
  local delay_cap="${BOUNDED_RETRY_DELAY_CAP_SECONDS:-30}"
  local rc=1
  for ((attempt = 1; attempt <= max_attempts; attempt++)); do
    echo "bounded retry ${label}: attempt ${attempt}/${max_attempts}"
    if python3 "$_BOUNDED_RETRY_DIR/bounded_timeout.py" \
      --seconds "$seconds" -- "$@"; then
      return 0
    else
      rc=$?
    fi

    if [ "$attempt" -ge "$max_attempts" ]; then
      break
    fi

    local sleep_seconds=$((attempt * retry_delay))
    if [ "$sleep_seconds" -gt "$delay_cap" ]; then
      sleep_seconds="$delay_cap"
    fi
    echo "::warning title=Bounded external retry::${label}" \
      "failed with exit ${rc}; retrying in ${sleep_seconds}s."
    sleep "$sleep_seconds"
  done

  echo "::error title=Bounded external retry exhausted::${label}" \
    "failed after ${max_attempts} attempts (last exit ${rc})." >&2
  return "$rc"
}
