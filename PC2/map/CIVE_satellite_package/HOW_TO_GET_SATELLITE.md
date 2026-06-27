# How to Get Real Satellite Imagery for UDOM CIVE — Step by Step

## Overview
You need a PNG file of the actual CIVE campus from above.
There are 3 ways, from easiest to most technical.

---

## METHOD 1 — QGIS (Recommended, free, 10 minutes)

QGIS is free GIS software. It can pull live satellite tiles and
export them as a PNG you paste straight into Webots.

### Step 1 — Install QGIS
```
https://qgis.org/download/
```
Works on Ubuntu 24.04:
```bash
sudo apt install qgis
```

### Step 2 — Add ESRI satellite layer
1. Open QGIS
2. In the Browser panel → right-click XYZ Tiles → New Connection
3. Fill in:
   - Name:  ESRI World Imagery
   - URL:   https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}
   - Max zoom: 19
4. Click OK → double-click the new layer to add it

### Step 3 — Navigate to CIVE
1. View → Panels → Coordinate (enable it)
2. In the coordinate box type:   35.81396,-6.21745
3. Press Enter — map flies to CIVE
4. Zoom in until you can see individual buildings

### Step 4 — Export as image
1. Project → Import/Export → Export Map to Image
2. Set extent: draw a box around the full CIVE campus
3. Resolution: 4096 × 4096 pixels
4. Format: PNG
5. Save as:  textures/satellite_cive.png

---

## METHOD 2 — Python Script (Automatic, runs on your machine)

The script `download_cive_satellite.py` does everything automatically.

### Step 1 — Install dependencies
```bash
pip install Pillow requests
```

### Step 2 — Run the script
```bash
python3 download_cive_satellite.py
```

It will:
- Download 121 satellite tiles (11×11 grid) from ESRI
- Stitch them into a 4096×4096 PNG
- Tell you exactly what size to use in your .wbt file

### Step 3 — If ESRI tiles are blocked on your network
Edit the script, change ZOOM from 19 to 18 (fewer tiles = faster).
Or try zoom 17 first to confirm the pipeline works.

---

## METHOD 3 — Google Earth Screenshot (Zero tools, 2 minutes)

1. Open Google Earth (earth.google.com/web)
2. Search:  University of Dodoma CIVE
3. Zoom in to show the full campus
4. Screenshot the window (scrot, gnome-screenshot, or PrintScreen)
5. Crop to just the campus area in GIMP or any image editor
6. Resize to 4096×4096 and save as satellite_cive.png

This is lower quality but works immediately with zero setup.

---

## Step (same for all methods) — Apply texture in Webots

Replace the ground Solid in UDOM_CIVE_realistic.wbt:

```
Solid {
  name "ground"
  children [
    Shape {
      appearance PBRAppearance {
        baseColorMap ImageTexture { url "../textures/satellite_cive.png" }
        roughness 1.0
        metalness 0.0
      }
      geometry Plane { size 836 836 }
    }
  ]
  boundingObject Plane { size 836 836 }
  locked TRUE
}
```

The size 836 × 836 metres was calculated from the GPS bounds of
the 11×11 tile grid at zoom 19 centred on CIVE.

---

## Verifying alignment with QGroundControl

Your world file already has:
  gpsReference -6.21745 35.81396 1120

This means the Webots origin (0,0,0) maps exactly to the GPS centre
of the satellite image. When QGroundControl shows the drone's
GPS position on its map, it will match the simulation.

To verify:
1. Start the Webots simulation
2. Open QGroundControl → it connects via MAVLink on UDP 14550
3. The drone icon on QGroundControl's map should sit on top of CIVE

---

## Optimal texture resolution guide

| Zoom | m/pixel | Tile grid | PNG size | Use case               |
|------|---------|-----------|----------|------------------------|
| 17   | 1.2 m   | 3×3       | 768px    | Quick test             |
| 18   | 0.6 m   | 5×5       | 1280px   | Good detail            |
| 19   | 0.3 m   | 11×11     | 4096px   | Best — individual trees|
| 20   | 0.15 m  | 21×21     | 4096px   | Extreme (slow)         |

Zoom 19 is the sweet spot for obstacle detection work.
