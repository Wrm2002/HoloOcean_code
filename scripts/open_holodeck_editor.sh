#!/usr/bin/env bash
set -euo pipefail

UE_EDITOR="/home/wrm/UnrealEngine/UE_5.3/Engine/Binaries/Linux/UnrealEditor"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${WRM_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PROJECT="$PROJECT_ROOT/engine/Holodeck.uproject"

exec "$UE_EDITOR" "$PROJECT"
