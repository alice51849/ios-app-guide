#!/usr/bin/env bash

# Merge a fixed remote tip into the generated tree before every bounded push
# attempt. Callers provide the phase-specific reconciliation and gate function.

remote_first_run_timed() {
  local seconds="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$seconds" "$@"
  else
    "$@"
  fi
}

remote_first_abort_merge() {
  if git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
    git merge --abort || true
  fi
}

remote_first_run_reconcile() {
  local callback="$1"
  local budget="${2:-}"
  local definition

  definition="$(declare -f "$callback")" || return 1
  if [ -n "$budget" ] && command -v timeout >/dev/null 2>&1; then
    # Bound the reconcile by the job's remaining budget so a slow attempt
    # fails here with a clear error instead of being cancelled mid-step by
    # the job timeout (2026-10-29 run 40887904887 sat 46 minutes in a
    # reconcile and was cancelled with nothing published).
    timeout --kill-after=30 "$budget" bash -euo pipefail -c \
      "${definition}"$'\n''"$1"' \
      remote-first-reconcile "$callback"
  else
    bash -euo pipefail -c \
      "${definition}"$'\n''"$1"' \
      remote-first-reconcile "$callback"
  fi
}

# Seconds left before REMOTE_FIRST_DEADLINE_EPOCH, or empty when no deadline
# is configured. Never negative.
remote_first_seconds_left() {
  local deadline="${REMOTE_FIRST_DEADLINE_EPOCH:-}"
  local left

  if [ -z "$deadline" ]; then
    return 0
  fi
  left=$((deadline - $(date +%s)))
  if [ "$left" -lt 0 ]; then
    left=0
  fi
  printf '%s\n' "$left"
}

integrate_origin_main() {
  local remote="${1:-origin}"
  local branch="${2:-main}"
  local timeout_seconds="${REMOTE_FIRST_TIMEOUT_SECONDS:-180}"
  local path
  local saw_conflict=0

  if ! remote_first_run_timed \
    "$timeout_seconds" git fetch --no-tags "$remote" "$branch"; then
    echo "::warning::unable to fetch ${remote}/${branch}"
    return 1
  fi
  REMOTE_SHA="$(git rev-parse FETCH_HEAD)" || return 1
  export REMOTE_SHA

  if git merge-base --is-ancestor "$REMOTE_SHA" HEAD; then
    return 0
  fi

  if ! git merge --no-edit -X theirs "$REMOTE_SHA"; then
    if ! git rev-parse -q --verify MERGE_HEAD >/dev/null 2>&1; then
      return 1
    fi
    while IFS= read -r -d '' path; do
      saw_conflict=1
      if git cat-file -e "${REMOTE_SHA}:${path}" 2>/dev/null; then
        if ! git restore \
          --source="$REMOTE_SHA" --staged --worktree -- "$path"; then
          remote_first_abort_merge
          return 1
        fi
      elif ! git rm -f -- "$path"; then
        remote_first_abort_merge
        return 1
      fi
    done < <(git diff --name-only --diff-filter=U -z)

    if [ "$saw_conflict" != "1" ] \
      || [ -n "$(git diff --name-only --diff-filter=U)" ]; then
      remote_first_abort_merge
      return 1
    fi
    if ! git commit --no-edit; then
      remote_first_abort_merge
      return 1
    fi
  fi

  git merge-base --is-ancestor "$REMOTE_SHA" HEAD
}

remote_first_publish() {
  local reconcile_callback="$1"
  local remote="${2:-origin}"
  local branch="${3:-main}"
  local max_attempts="${4:-5}"
  local timeout_seconds="${REMOTE_FIRST_TIMEOUT_SECONDS:-180}"
  local retry_delay="${REMOTE_FIRST_RETRY_DELAY_SECONDS:-10}"
  local min_reconcile="${REMOTE_FIRST_MIN_RECONCILE_SECONDS:-0}"
  local needed="$min_reconcile"
  local attempt
  local left
  local budget
  local started
  local status

  if ! declare -F "$reconcile_callback" >/dev/null 2>&1; then
    echo "::error::missing reconciliation callback: ${reconcile_callback}"
    return 1
  fi

  for ((attempt = 1; attempt <= max_attempts; attempt++)); do
    REMOTE_FIRST_ATTEMPTS_USED="$attempt"
    export REMOTE_FIRST_ATTEMPTS_USED
    echo "remote-first publish attempt ${attempt}/${max_attempts}"

    left="$(remote_first_seconds_left)"
    budget=""
    if [ -n "$left" ]; then
      # Do not start an attempt the job cannot finish: the reconcile needs at
      # least as long as the slowest attempt so far (or the configured floor)
      # plus one bounded push. Stop with a clear error and push nothing; the
      # next scheduled run regenerates from the newer main.
      if [ "$left" -le "$((needed + timeout_seconds))" ]; then
        echo "::error::not enough job time left for publish attempt ${attempt} (${left}s left, needs about $((needed + timeout_seconds))s); stopping without push so the next run regenerates from current main"
        return 1
      fi
      budget="$((left - timeout_seconds))"
    fi

    if integrate_origin_main "$remote" "$branch"; then
      # A function called from `if ! ...` inherits Bash's errexit immunity.
      # Run it in a fresh strict shell so any intermediate gate failure stops
      # before staging or publishing.
      started="$(date +%s)"
      status=0
      remote_first_run_reconcile "$reconcile_callback" "$budget" || status=$?
      if [ "$status" -ne 0 ]; then
        if [ -n "$budget" ] && { [ "$status" -eq 124 ] || [ "$status" -eq 137 ]; }; then
          echo "::error::${reconcile_callback} ran out of the job time budget (${budget}s); refusing to push"
        else
          echo "::error::${reconcile_callback} failed; refusing to push"
        fi
        return 1
      fi
      if [ "$(($(date +%s) - started))" -gt "$needed" ]; then
        needed="$(($(date +%s) - started))"
      fi
      git add -A || return 1
      if ! git diff --cached --quiet; then
        git commit -m \
          "${REMOTE_FIRST_RECONCILE_MESSAGE:-Reconcile generated tree after origin merge}" \
          || return 1
      fi
      if ! git merge-base --is-ancestor "$REMOTE_SHA" HEAD; then
        echo "::error::fetched origin tip is not an ancestor of HEAD"
        return 1
      fi
      if declare -F remote_first_before_push >/dev/null 2>&1; then
        remote_first_before_push "$attempt" "$REMOTE_SHA" || return 1
      fi
      if remote_first_run_timed \
        "$timeout_seconds" \
        git push "$remote" "HEAD:refs/heads/${branch}"; then
        return 0
      fi
      echo "push rejected after attempt ${attempt}; main moved or push failed"
    fi

    if [ "$attempt" -lt "$max_attempts" ]; then
      sleep "$((attempt * retry_delay))"
    fi
  done

  echo "::error::main kept moving after ${max_attempts} bounded merge attempts"
  return 1
}
