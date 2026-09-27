#!/usr/bin/env bash
# Publish NoticeGuard to the shared Hetzner box → https://noticeguard.ruleandrecord.com
#   bash deploy/publish.sh
# Conventions (same as the other services on the box): app in /opt/noticeguard, container on the existing Caddy
# network, Caddy drop-in in /opt/caddy-sites, zero-downtime `caddy reload`. Touches nothing else on the box.
set -euo pipefail
HOST=${SERVER:-root@37.27.202.168}
APP_DIR=/opt/noticeguard
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [ ! -f "$ROOT/deploy/.env" ]; then
  echo "no deploy/.env found; using deploy/.env.example (demo runs from cache, live uploads need a key)"
  cp "$ROOT/deploy/.env.example" "$ROOT/deploy/.env"
fi

echo "==> rsync sources to $HOST:$APP_DIR"
ssh "$HOST" "mkdir -p $APP_DIR /opt/caddy-sites"
rsync -az --delete --exclude .env --exclude .venv --exclude __pycache__ --exclude .pytest_cache --exclude .git --exclude 'data/cases.db' \
  "$ROOT/app" "$ROOT/static" "$ROOT/data" "$ROOT/cache" "$ROOT/bench" "$ROOT/deploy" "$ROOT/requirements.txt" "$ROOT/README.md" "$HOST:$APP_DIR/"
scp -q "$ROOT/deploy/.env" "$HOST:$APP_DIR/deploy/.env"
ssh "$HOST" "chmod 600 $APP_DIR/deploy/.env"

echo "==> build + start"
ssh "$HOST" "cd $APP_DIR/deploy && docker compose build noticeguard && docker compose up -d noticeguard"

echo "==> caddy drop-in + reload"
rsync -az "$ROOT/deploy/noticeguard.caddy" "$HOST:/opt/caddy-sites/noticeguard.caddy"
ssh "$HOST" "cd /opt/compass/deploy && docker compose exec -T caddy caddy reload --config /etc/caddy/Caddyfile"

echo "==> health"
sleep 3
ssh "$HOST" "curl -sf http://127.0.0.1:8790/api/health && echo"
curl -sS -o /dev/null -w "https://noticeguard.ruleandrecord.com  HTTP %{http_code}\n" --max-time 30 https://noticeguard.ruleandrecord.com/ || echo "  (first HTTPS hit may lag while Let's Encrypt issues the cert)"
