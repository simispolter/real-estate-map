#!/bin/sh
set -eu

LOCKFILE_PATH="/workspace/package-lock.json"
NODE_MODULES_DIR="/workspace/node_modules"
NEXT_BUILD_DIR="/workspace/apps/web/.next"
LOCKFILE_STAMP="$NODE_MODULES_DIR/.package-lock.sha256"

mkdir -p "$NODE_MODULES_DIR" "$NEXT_BUILD_DIR"

CURRENT_LOCKFILE_SHA="$(sha256sum "$LOCKFILE_PATH" | awk '{ print $1 }')"
PREVIOUS_LOCKFILE_SHA=""

if [ -f "$LOCKFILE_STAMP" ]; then
  PREVIOUS_LOCKFILE_SHA="$(cat "$LOCKFILE_STAMP")"
fi

if [ ! -d "$NODE_MODULES_DIR/next" ] || [ "$CURRENT_LOCKFILE_SHA" != "$PREVIOUS_LOCKFILE_SHA" ]; then
  npm ci
  printf '%s' "$CURRENT_LOCKFILE_SHA" > "$LOCKFILE_STAMP"
  rm -rf "${NEXT_BUILD_DIR:?}/"*
fi

exec npm run dev --workspace @real-estat-map/web -- --hostname 0.0.0.0 --port 3000
