#!/usr/bin/env bash

geo_require_natural_root() {
  local event_name="${GITHUB_EVENT_NAME:-}"
  local run_attempt="${GITHUB_RUN_ATTEMPT:-}"
  if [ "$event_name" != "schedule" ] || [ "$run_attempt" != "1" ]; then
    echo "::error title=Non-natural GEO root rejected::event=${event_name}" \
      "run_attempt=${run_attempt}; only schedule attempt 1 may publish."
    return 78
  fi
}

geo_refresh_utc_date() {
  local now="${1:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
  if ! [[ "$now" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
    echo "invalid UTC timestamp: ${now}" >&2
    return 64
  fi
  export TZ=UTC
  export GEO_CLOCK_AT="$now"
  export GEO_BUILD_DATE="${now%%T*}"
}
