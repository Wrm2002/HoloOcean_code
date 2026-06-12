#!/bin/sh
set -eu

PROJECT="/home/wrm/holoocean/engine/Holodeck.uproject"
UAT="/home/wrm/UnrealEngine/UE_5.3/Engine/Build/BatchFiles/RunUAT.sh"
PACKAGE_DIR="${1:-/home/wrm/holoocean/wrm_projects/04_wrmabyss_holoocean_package/WRMAbyss}"
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
