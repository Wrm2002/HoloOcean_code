#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT="${WRM_PROJECT_ROOT:-$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)}"
PROJECT="$PROJECT_ROOT/engine/Holodeck.uproject"
UE_ROOT="${WRM_UNREAL_ROOT:-$HOME/UnrealEngine/UE_5.3}"
UAT="${WRM_UAT:-$UE_ROOT/Engine/Build/BatchFiles/RunUAT.sh}"
PACKAGE_DIR="${1:-$PROJECT_ROOT/wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss}"
MAPS="${2:-/Game/WRMRouteB/Maps/SonarSmoke+/Game/WRMRouteB/Maps/BigWorldLiteSmoke+/Game/WRMRouteB/Maps/BigWorldLite4x4Smoke+/Game/WRMRouteB/Maps/GaeaErosion2Mesh4x4Smoke+/Game/WRMRouteB/Maps/GaeaErosion2AuvSurvey01+/Game/WRMRouteB/Maps/GaeaErosion2AuvSurveyUnderwater+/Game/BigWorld4K20260609/Maps/Main_World_10km_4K_20260609}"

mkdir -p "$PACKAGE_DIR"

exec "$UAT" BuildCookRun \
  -project="$PROJECT" \
  -noP4 \
  -platform=Linux \
  -clientconfig=Development \
  -serverconfig=Development \
  -build \
  -cook \
  -map="$MAPS" \
  -stage \
  -pak \
  -archive \
  -archivedirectory="$PACKAGE_DIR" \
  -utf8output
