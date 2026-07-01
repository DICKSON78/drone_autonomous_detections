#!/usr/bin/env python3
"""
UDOM CIVE Campus — Satellite Tile Downloader & Stitcher
========================================================
Downloads satellite imagery tiles from OpenStreetMap/ESRI for the CIVE campus
and stitches them into a single PNG ready to use as a Webots ground texture.

Uses ESRI World Imagery (free, no API key needed, high-res for Africa).
Falls back to OpenStreetMap if ESRI is unavailable.

GPS centre:  -6.21745, 35.81396  (UDOM CIVE)
Coverage:    ~600 m × 600 m  (matches the Webots world size)
Zoom level:  19  (≈ 0.3 m/pixel — you can see individual trees)

Usage:
    pip install Pillow requests
    python3 download_cive_satellite.py

Output:
    textures/satellite_cive.png   — 4096×4096 stitched texture
    textures/satellite_cive_meta.txt — geo-bounds for reference
"""

import os, math, time, sys
import requests
from PIL import Image
from io import BytesIO

# ── Configuration ────────────────────────────────────────────────────────────

LAT      = -6.21745   # CIVE campus centre latitude
LON      = 35.81396   # CIVE campus centre longitude
ZOOM     = 19         # 19 = ~0.3 m/pixel (best detail); use 18 if tiles are missing
RADIUS_M = 350        # metres from centre to edge — covers ~700×700 m campus

OUT_DIR  = os.path.join(os.path.dirname(__file__), "textures")
OUT_FILE = os.path.join(OUT_DIR, "satellite_cive.png")
META_FILE = os.path.join(OUT_DIR, "satellite_cive_meta.txt")

TILE_SIZE = 256  # pixels per tile (standard)

# Tile sources (tried in order)
SOURCES = [
    # ESRI World Imagery — best resolution for East Africa, free, no key
    {
        "name": "ESRI World Imagery",
        "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        "headers": {"User-Agent": "UDOM-CIVE-Drone-Research/1.0"}
    },
    # OpenStreetMap fallback (no satellite but good for testing pipeline)
    {
        "name": "OpenTopoMap",
        "url": "https://tile.opentopomap.org/{z}/{x}/{y}.png",
        "headers": {"User-Agent": "UDOM-CIVE-Drone-Research/1.0 (academic use)"}
    }
]

# ── Coordinate math ──────────────────────────────────────────────────────────

def lat_lon_to_tile(lat, lon, zoom):
    """Convert GPS coordinates to tile x,y at given zoom."""
    n = 2 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(lat)
    y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    return x, y

def tile_to_lat_lon(x, y, zoom):
    """Convert tile x,y to top-left GPS corner."""
    n = 2 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_r = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_r)
    return lat, lon

def metres_to_tiles(metres, lat, zoom):
    """How many tiles span N metres at this latitude/zoom."""
    # Earth circumference at this latitude
    circ = 2 * math.pi * 6378137 * math.cos(math.radians(lat))
    metres_per_tile = circ / (2 ** zoom) / TILE_SIZE * TILE_SIZE
    return max(1, math.ceil(metres / metres_per_tile))

# ── Download ─────────────────────────────────────────────────────────────────

def download_tile(x, y, z, source):
    url = source["url"].format(x=x, y=y, z=z)
    try:
        resp = requests.get(url, headers=source["headers"], timeout=15)
        if resp.status_code == 200 and len(resp.content) > 500:
            return Image.open(BytesIO(resp.content)).convert("RGB")
    except Exception as e:
        pass
    return None

# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # Centre tile
    cx, cy = lat_lon_to_tile(LAT, LON, ZOOM)

    # How many tiles do we need each side?
    half_tiles = metres_to_tiles(RADIUS_M, LAT, ZOOM)
    half_tiles = max(2, min(half_tiles, 6))  # clamp 2–6 tiles each side

    x0 = cx - half_tiles
    x1 = cx + half_tiles
    y0 = cy - half_tiles
    y1 = cy + half_tiles

    nx = x1 - x0 + 1
    ny = y1 - y0 + 1

    print(f"\nUDOM CIVE Satellite Downloader")
    print(f"Centre:  {LAT}, {LON}")
    print(f"Zoom:    {ZOOM}  (~{int(156543.03392 * math.cos(math.radians(LAT)) / (2**ZOOM))} cm/pixel)")
    print(f"Grid:    {nx} × {ny} tiles  ({nx * TILE_SIZE} × {ny * TILE_SIZE} px raw)")
    print(f"Output:  {OUT_FILE}\n")

    canvas = Image.new("RGB", (nx * TILE_SIZE, ny * TILE_SIZE), (180, 160, 120))

    source = None
    total = nx * ny
    done = 0

    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            px = (tx - x0) * TILE_SIZE
            py = (ty - y0) * TILE_SIZE
            done += 1

            # Try each source
            tile_img = None
            for src in SOURCES:
                if source and src["name"] != source["name"]:
                    continue  # stick with working source
                tile_img = download_tile(tx, ty, ZOOM, src)
                if tile_img:
                    source = src
                    break

            if tile_img:
                canvas.paste(tile_img, (px, py))
                print(f"  [{done}/{total}] tile ({tx},{ty}) ✓  via {source['name']}")
            else:
                print(f"  [{done}/{total}] tile ({tx},{ty}) ✗  (blank filled)")

            time.sleep(0.08)  # polite rate limit

    # Resize to power-of-2 for Webots (max 4096×4096)
    target = 4096
    final = canvas.resize((target, target), Image.LANCZOS)
    final.save(OUT_FILE, "PNG", optimize=True)

    # Write geo metadata
    top_lat,  left_lon  = tile_to_lat_lon(x0,     y0,     ZOOM)
    bot_lat,  right_lon = tile_to_lat_lon(x1 + 1, y1 + 1, ZOOM)

    # Approximate real-world size in metres
    lat_m = (top_lat - bot_lat) * 111320
    lon_m = (right_lon - left_lon) * 111320 * math.cos(math.radians(LAT))

    meta = f"""UDOM CIVE Satellite Texture Metadata
======================================
GPS centre:    {LAT}, {LON}
Zoom level:    {ZOOM}
Tile grid:     {nx} x {ny}
Bounds:
  North:  {top_lat:.6f}
  South:  {bot_lat:.6f}
  West:   {left_lon:.6f}
  East:   {right_lon:.6f}
Real-world size:
  N-S:    {lat_m:.1f} m
  E-W:    {lon_m:.1f} m

Webots ground plane size to use:
  geometry Plane {{ size {lon_m:.0f} {lat_m:.0f} }}

Source: {source['name'] if source else 'none'}
"""
    with open(META_FILE, "w") as f:
        f.write(meta)

    print(f"\n✓ Saved: {OUT_FILE}  ({target}×{target} px)")
    print(f"✓ Meta:  {META_FILE}")
    print(f"\nReal-world coverage:  {lon_m:.0f} m E-W  ×  {lat_m:.0f} m N-S")
    print(f"\nPaste this into your .wbt ground Solid:")
    print(f"""
  Shape {{
    appearance PBRAppearance {{
      baseColorMap ImageTexture {{ url "../textures/satellite_cive.png" }}
      roughness 1.0  metalness 0.0
    }}
    geometry Plane {{ size {lon_m:.0f} {lat_m:.0f} }}
  }}
""")

if __name__ == "__main__":
    main()
