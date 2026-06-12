#!/usr/bin/env bash
set -euo pipefail

UE_ROOT="${WRM_UNREAL_ROOT:-$HOME/UnrealEngine/UE_5.3}"
UE_EDITOR="${WRM_UE_EDITOR:-$UE_ROOT/Engine/Binaries/Linux/UnrealEditor}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${WRM_PROJECT_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
PROJECT="$PROJECT_ROOT/engine/Holodeck.uproject"

exec "$UE_EDITOR" "$PROJECT"
