#!/usr/bin/env bash

_BOUNDED_RESUMABLE_DIR="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1
  pwd
)"

run_bounded_resumable() {
  if [ "$#" -lt 3 ]; then
    echo "run_bounded_resumable requires: seconds label command..." >&2
    return 64
  fi

  local seconds="$1"
  local label="$2"
  shift 2
  local rc

  if python3 "$_BOUNDED_RESUMABLE_DIR/bounded_timeout.py" \
    --seconds "$seconds" -- "$@"; then
    rc=0
  else
    rc=$?
  fi

  case "$rc" in
    0)
      return 0
      ;;
    124)
      echo "::warning title=Bounded localization pass::${label}" \
        "reached its ${seconds}s bound (normalized exit 124);" \
        "the final full gate remains authoritative."
      return 0
      ;;
    *)
      echo "::error title=Localization failed::${label} exited ${rc};" \
        "aborting before the final full gate." >&2
      return "$rc"
      ;;
  esac
}
