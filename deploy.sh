#!/bin/bash
# Deploy chaoschanneling.com — safe: backs up the Caddyfile, validates BEFORE
# reloading, and restores the backup if validation fails (so the other live
# sites — chaoscommand.center etc. — can never be knocked offline).
# Run as: echo "$SUDO_PW" | sudo -S bash /mnt/win-d/Ace/chaoschanneling-site/deploy.sh
set -e
SRC=/mnt/win-d/Ace/chaoschanneling-site
WEBROOT=/var/www/chaoschanneling.com
CADDY=/etc/caddy/Caddyfile
TS=$(date +%Y%m%d-%H%M%S)

echo "→ backing up Caddyfile to ${CADDY}.bak.${TS}"
cp "$CADDY" "${CADDY}.bak.${TS}"

echo "→ creating webroot + copying site"
mkdir -p "$WEBROOT"
cp "$SRC/index.html" "$WEBROOT/"

if grep -q 'chaoschanneling.com {' "$CADDY"; then
  echo "→ Caddy block already present; not re-adding"
else
  echo "→ appending Caddy block"
  cat "$SRC/caddy-block.txt" >> "$CADDY"
fi

echo "→ validating Caddy config"
if caddy validate --config "$CADDY" --adapter caddyfile; then
  echo "→ valid; reloading Caddy"
  systemctl reload caddy
  echo "DEPLOY OK ✅"
else
  echo "✗ VALIDATION FAILED — restoring backup, NOT reloading"
  cp "${CADDY}.bak.${TS}" "$CADDY"
  exit 1
fi
