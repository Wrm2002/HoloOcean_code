#!/usr/bin/env bash
set -euo pipefail

UE_EDITOR="/home/wrm/UnrealEngine/UE_5.3/Engine/Binaries/Linux/UnrealEditor"
PROJECT="/home/wrm/holoocean/engine/Holodeck.uproject"

exec "$UE_EDITOR" "$PROJECT"
