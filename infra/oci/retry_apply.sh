#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

MAX_ATTEMPTS="${MAX_ATTEMPTS:-0}"      # 0 = infinite
SLEEP_SECONDS="${SLEEP_SECONDS:-300}"  # 5 minutes
LOG_FILE="${LOG_FILE:-retry-apply.log}"

if [[ ! -d .terraform ]]; then
  terraform init
fi

attempt=1

while true; do
  printf '%s attempt=%s: terraform apply\n' "$(date -Iseconds)" "$attempt" | tee -a "$LOG_FILE"

  set +e
  terraform apply -auto-approve 2>&1 | tee -a "$LOG_FILE"
  status="${PIPESTATUS[0]}"
  set -e

  if [[ "$status" -eq 0 ]]; then
    printf '%s success\n' "$(date -Iseconds)" | tee -a "$LOG_FILE"
    exit 0
  fi

  if grep -Eiq "Out of host capacity|Out of capacity for shape" "$LOG_FILE"; then
    printf '%s out-of-capacity; sleeping %ss\n' "$(date -Iseconds)" "$SLEEP_SECONDS" | tee -a "$LOG_FILE"
  else
    printf '%s terraform failed (non-capacity); exiting\n' "$(date -Iseconds)" | tee -a "$LOG_FILE"
    exit "$status"
  fi

  if [[ "$MAX_ATTEMPTS" -ne 0 && "$attempt" -ge "$MAX_ATTEMPTS" ]]; then
    printf '%s reached MAX_ATTEMPTS=%s; exiting\n' "$(date -Iseconds)" "$MAX_ATTEMPTS" | tee -a "$LOG_FILE"
    exit 1
  fi

  attempt="$((attempt + 1))"
  sleep "$SLEEP_SECONDS"
done

