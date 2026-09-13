#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE:?IMAGE is required}"
: "${TRAEFIK_HOST:?TRAEFIK_HOST is required}"
: "${DASHBOARD_USERNAME:?DASHBOARD_USERNAME is required}"
: "${DASHBOARD_PASSWORD_HASH:?DASHBOARD_PASSWORD_HASH is required}"
: "${DASHBOARD_SESSION_SECRET:?DASHBOARD_SESSION_SECRET is required}"

for name in IMAGE TRAEFIK_HOST DASHBOARD_USERNAME DASHBOARD_PASSWORD_HASH DASHBOARD_SESSION_SECRET; do
  if [[ "${!name}" == *$'\n'* || "${!name}" == *$'\r'* ]]; then
    echo "Invalid multiline value for $name." >&2
    exit 1
  fi
done

if [[ ! "$DASHBOARD_PASSWORD_HASH" =~ ^scrypt\$[0-9]+\$[0-9]+\$[0-9]+\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+$ ]]; then
  echo 'Invalid dashboard password hash format.' >&2
  exit 1
fi

printf 'IMAGE=%s\n' "$IMAGE"
printf 'TRAEFIK_HOST=%s\n' "$TRAEFIK_HOST"
# Escape dotenv quoting and Compose interpolation independently.
quote_value() {
  local value="$1"
  value="${value//\\/\\\\}"
  value="${value//\"/\\\"}"
  value="${value//\$/\$\$}"
  printf '"%s"' "$value"
}
printf 'DASHBOARD_USERNAME=%s\n' "$(quote_value "$DASHBOARD_USERNAME")"
printf 'DASHBOARD_PASSWORD_HASH=%s\n' "$(quote_value "$DASHBOARD_PASSWORD_HASH")"
printf 'DASHBOARD_SESSION_SECRET=%s\n' "$(quote_value "$DASHBOARD_SESSION_SECRET")"
