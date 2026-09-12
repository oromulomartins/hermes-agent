#!/usr/bin/env sh
set -eu

app_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$app_dir"

test -f .env.next
test -f docker-compose.yml
docker network inspect compose_hermes_net >/dev/null

previous_image=""
if [ -f .env ]; then
  previous_image=$(sed -n 's/^IMAGE=//p' .env | head -n 1)
fi

install -m 600 .env.next .env
rm -f .env.next

rollback() {
  if [ -n "$previous_image" ]; then
    sed "s|^IMAGE=.*|IMAGE=$previous_image|" .env > .env.rollback
    install -m 600 .env.rollback .env
    rm -f .env.rollback
    docker compose pull dashboard
    docker compose up -d dashboard
  else
    docker compose down
  fi
}

if ! docker compose pull dashboard || ! docker compose up -d dashboard; then
  rollback
  exit 1
fi

hostname=$(sed -n 's/^TRAEFIK_HOST=//p' .env | head -n 1)
attempt=1
while [ "$attempt" -le 15 ]; do
  status=$(curl -ksS -o /dev/null -w '%{http_code}' --resolve "$hostname:443:127.0.0.1" "https://$hostname/" || true)
  case "$status" in
    200|302|401) exit 0 ;;
  esac
  attempt=$((attempt + 1))
  sleep 2
done

rollback
exit 1
