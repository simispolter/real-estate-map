#!/bin/sh
set -eu

NEXT_BUILD_DIR="/workspace/apps/web/.next"

mkdir -p "$NEXT_BUILD_DIR"
rm -rf "${NEXT_BUILD_DIR:?}/"*

npm ci

exec npm run dev --workspace @real-estat-map/web -- --hostname 0.0.0.0 --port 3000
