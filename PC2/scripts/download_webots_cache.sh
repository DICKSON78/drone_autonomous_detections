#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# Pre-populate Webots snap asset cache.
#
# Webots snap cache scheme: SHA1(url) → file content
#   hash = $(echo -n "$url" | sha1sum | cut -d' ' -f1)
#   file = assets/<hash>
#
# We iterate all EXTERNPROTO URLs from the world file, download each,
# store at assets/SHA1(url). Then scan each PROTO for embedded texture/mesh
# URLs, resolve relative paths, and download those too.
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

GBASE="https://raw.githubusercontent.com/cyberbotics/webots/R2025a"
ASSETS="$HOME/snap/webots/common/.cache/Cyberbotics/Webots/assets"
mkdir -p "$ASSETS"

hash_of() { echo -n "$1" | sha1sum | cut -d' ' -f1; }

# ── 1. All EXTERNPROTO URLs from the world file ──────────────────────────────
WORLD="/home/dickson/FYP/drone_autonomous/PC2/webots/worlds/mavic2pro_px4.wbt"
URLS=($(grep 'EXTERNPROTO' "$WORLD" | grep -v 'protos/Mavic2Pro' | sed "s/.*\"\(.*\)\"/\1/"))

# Add known dependency PROTOs (referenced by other PROTOs)
URLS+=(
  "$GBASE/projects/objects/road/protos/RoadLine.proto"
  "$GBASE/projects/objects/road/protos/CrashBarrier.proto"
  "$GBASE/projects/objects/buildings/protos/Building.proto"
  "$GBASE/projects/vehicles/protos/tesla/TeslaModel3Wheel.proto"
  "$GBASE/projects/vehicles/protos/tesla/TeslaModel3Coachwork.proto"
  "$GBASE/projects/vehicles/protos/tesla/TeslaModel3Windows.proto"
  "$GBASE/projects/vehicles/protos/tesla/TeslaModel3FrontLights.proto"
  "$GBASE/projects/vehicles/protos/tesla/TeslaModel3Details.proto"
)

# ── 2. Download a single URL and cache by SHA1(url) ────────────────────────────
fetch() {
  local url="$1"
  [ -z "$url" ] && return 0
  local hash=$(hash_of "$url")
  [ -f "$ASSETS/$hash" ] && return 0
  local fname="${url##*/}"
  local tmpf=$(mktemp)
  if curl -sL --connect-timeout 10 --max-time 120 "$url" -o "$tmpf" 2>/dev/null && [ -s "$tmpf" ]; then
    mv "$tmpf" "$ASSETS/$hash"
    echo "  ✓ $fname → $hash"
  else
    rm -f "$tmpf"
    echo "  ✗ $fname"
  fi
}

# ── 3. Scan a cached PROTO file for texture/mesh/referenced URLs ──────────────
#     Relative paths like "textures/foo.jpg" are resolved against the proto URL.
extract_urls_from_proto() {
  local proto_url="$1"
  local proto_hash=$(hash_of "$proto_url")
  local proto_file="$ASSETS/$proto_hash"
  [ -f "$proto_file" ] || { echo "DEBUG: MISSING $proto_file" >&2; return; }

  # Compute base directory of the proto URL  
  local base="${proto_url%/*}/"

  # Extract EXTERNPROTO references
  grep "EXTERNPROTO" "$proto_file" 2>/dev/null | sed 's/.*"\(.*\)"/\1/' | while read -r epath; do
    [ -z "$epath" ] && continue
    case "$epath" in
      http*|https*) echo "$epath" ;;
      /*)           echo "$GBASE$epath" ;;
      *)            echo "${base}${epath}" ;;
    esac
  done

  # Extract IMPORT references
  grep "import.*from" "$proto_file" 2>/dev/null | grep -oP "'[^']+\.js'" | sed "s/'//g" | while read -r ipath; do
    case "$ipath" in
      http*|https*) echo "$ipath" ;;
      /*)           echo "$GBASE$ipath" ;;
      *)            echo "${base}${ipath}" ;;
    esac
  done

  # Extract texture/image/mesh references from url fields
  # Match: "some/path/file.ext" where ext is image/mesh type
  grep -oP '"[^"]+\.(jpg|jpeg|png|dds|hdr|tiff|bmp|stl|obj)"' "$proto_file" 2>/dev/null | \
    sed 's/"//g' | sort -u | while read -r tpath; do
    [ -z "$tpath" ] && continue
    case "$tpath" in
      http*|https*) echo "$tpath" ;;
      /*)           echo "$GBASE$tpath" ;;
      *)            echo "${base}${tpath}" ;;
    esac
  done
}

# ── 4. Main ───────────────────────────────────────────────────────────────────
echo "[Cache] Populating Webots asset cache at $ASSETS"
echo "[Cache] $(find "$ASSETS" -type f | wc -l) files before"

# Phase A: Download all PROTO files
echo ""
echo "Phase A: PROTO files (${#URLS[@]} total)"
for url in "${URLS[@]}"; do
  fetch "$url"
done

# Phase B: Scan PROTOs for dependent textures/meshes and download them
echo ""
echo "Phase B: Texture/mesh dependencies"
ALL_CHILD_URLS=""
for url in "${URLS[@]}"; do
  child=$(extract_urls_from_proto "$url")
  ALL_CHILD_URLS="$ALL_CHILD_URLS
$child"
done
ALL_CHILD_URLS=$(echo "$ALL_CHILD_URLS" | sort -u | grep -v '^$' || true)
CHILD_COUNT=$(echo "$ALL_CHILD_URLS" | grep -c . || true)
echo "  Found $CHILD_COUNT unique dependencies"
echo "$ALL_CHILD_URLS" | while read -r child_url; do
  [ -z "$child_url" ] && continue
  fetch "$child_url"
done

echo ""
echo "[Cache] Done. $(find "$ASSETS" -type f | wc -l) files total"
