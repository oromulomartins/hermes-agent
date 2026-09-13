#!/usr/bin/env bash
set -euo pipefail

: "${IMAGE:?IMAGE is required}"
: "${TRAEFIK_HOST:?TRAEFIK_HOST is required}"
: "${DASHBOARD_USERNAME:?DASHBOARD_USERNAME is required}"
: "${DASHBOARD_PASSWORD_HASH:?DASHBOARD_PASSWORD_HASH is required}"
: "${DASHBOARD_SESSION_SECRET:?DASHBOARD_SESSION_SECRET is required}"

if [[ ! "$DASHBOARD_PASSWORD_HASH" =~ ^scrypt\$[0-9]+\$[0-9]+\$[0-9]+\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+$ ]]; then
  echo 'Invalid dashboard password hash format.' >&2
  exit 1
fi

printf 'IMAGE=%s\n' "$IMAGE"
printf 'TRAEFIK_HOST=%s\n' "$TRAEFIK_HOST"
printf 'DASHBOARD_USERNAME=%s\n' "$DASHBOARD_USERNAME"
# Compose interpolates dollar signs in unquoted dotenv values.
printf "DASHBOARD_PASSWORD_HASH='%s'\n" "$DASHBOARD_PASSWORD_HASH"
printf 'DASHBOARD_SESSION_SECRET=%s\n' "$DASHBOARD_SESSION_SECRET"
