#!/usr/bin/env python3
"""Generate a realistic UDOM CIVE Campus Webots world.

Based on OpenStreetMap data of the actual CIVE campus:
  - Administration, Auditorium, Library, Labs, Lecture rooms
  - Student hostels (Blocks 1-6), Cafeteria, Dispensary
  - Roads: Ujasi Road (dirt), Block 2/3 Road (asphalt)
  - Native Acacia trees, red/brown semi-arid soil

Uses local PROTOs (zero downloads for buildings).
"""

import os, sys, math, argparse

HOME_LAT = -6.1575
HOME_LON = 35.7605
HOME_ALT = 1123.0

WB = "https://raw.githubusercontent.com/cyberbotics/webots/R2025a"
LOCAL = "../protos"


def build(name, x, y, sx, sy, sz, wall=(0.82, 0.75, 0.58), roof=(0.60, 0.35, 0.20)):
    """Return a TanzaniaBuilding block (z = sz/2 so base sits on ground)."""
    return (f'TanzaniaBuilding {{\n'
            f'  translation {x} {y} {sz/2}\n'
            f'  name "{name}"\n'
            f'  size {sx} {sy} {sz}\n'
            f'  wallColor {wall[0]} {wall[1]} {wall[2]}\n'
            f'  roofColor {roof[0]} {roof[1]} {roof[2]}\n'
            f'}}')


def generate_world(output_path, include_drone=True):
    lines = []
    wl = lines.append

    wl('#VRML_SIM R2025a utf8')
    wl('')
    wl('# University of Dodoma — College of Informatics and Virtual Education')
    wl('# Based on OpenStreetMap data — actual CIVE buildings')
    wl('')

    externs = [
        f'EXTERNPROTO "{LOCAL}/Mavic2Pro.proto"',
        f'EXTERNPROTO "{LOCAL}/TanzaniaBuilding.proto"',
        f'EXTERNPROTO "{LOCAL}/AcaciaTree.proto"',
        f'EXTERNPROTO "{LOCAL}/Kiosk.proto"',
        f'EXTERNPROTO "{LOCAL}/MarketStall.proto"',
        f'EXTERNPROTO "{WB}/projects/objects/backgrounds/protos/TexturedBackground.proto"',
        f'EXTERNPROTO "{WB}/projects/objects/backgrounds/protos/TexturedBackgroundLight.proto"',
        f'EXTERNPROTO "{WB}/projects/objects/floors/protos/Floor.proto"',
        f'EXTERNPROTO "{WB}/projects/appearances/protos/SandyGround.proto"',
        f'EXTERNPROTO "{WB}/projects/appearances/protos/Asphalt.proto"',
        f'EXTERNPROTO "{WB}/projects/appearances/protos/Grass.proto"',
        f'EXTERNPROTO "{WB}/projects/objects/road/protos/Road.proto"',
        f'EXTERNPROTO "{WB}/projects/appearances/protos/Pavement.proto"',
        f'EXTERNPROTO "{WB}/projects/objects/buildings/protos/SimpleBuilding.proto"',
        f'EXTERNPROTO "{WB}/projects/objects/trees/protos/Pine.proto"',
        f'EXTERNPROTO "{WB}/projects/objects/traffic/protos/TrafficCone.proto"',
        f'EXTERNPROTO "{WB}/projects/vehicles/protos/tesla/TeslaModel3Simple.proto"',
    ]
    if not include_drone:
        externs = [e for e in externs if 'Mavic2Pro' not in e]
    for e in externs:
        wl(e)
    wl('')

    wl('WorldInfo {')
    wl('  info [')
    wl('    "University of Dodoma — College of Informatics and Virtual Education (CIVE)"')
    wl(f'    "GPS: {HOME_LAT:.6f}, {HOME_LON:.6f} | Alt: {HOME_ALT:.0f}m"')
    wl('    "Actual buildings from OSM: Admin, Library, Labs, Auditorium, 6 Blocks, Cafeteria, Dispensary"')
    wl('  ]')
    wl('  title "UDOM CIVE Campus"')
    wl('  basicTimeStep 16')
    wl('  defaultDamping Damping { linear 0.5 angular 0.5 }')
    wl('}')
    wl('')

    wl('Viewpoint {')
    wl('  orientation 0 0 1 0')
    wl('  position 0 -15 10')
    wl('  near 0.2')
    wl('  follow "Mavic 2 PRO"')
    wl('  followSmoothness 0.3')
    wl('}')
    wl('')

    wl('TexturedBackground { luminosity 4 }')
    wl('TexturedBackgroundLight {}')
    wl('')

    # ---- TERRAIN ----
    wl('Floor { size 600 600 tileSize 8 8')
    wl('  appearance SandyGround { colorOverride 0.70 0.62 0.42 }')
    wl('}')
    wl('')

    # ===== ACADEMIC BUILDINGS =====
    wl('# ======= ACADEMIC BUILDINGS =======')
    wl('')

    # 1. CIVE Administration
    wl('# CIVE Administration')
    wl(build("CIVE Admin", 0, -22, 20, 12, 9, (0.82, 0.75, 0.58), (0.60, 0.35, 0.20)))
    wl('')

    # 2. CIVE Auditorium
    wl('# CIVE Auditorium')
    wl(build("CIVE Auditorium", -22, -22, 20, 16, 8, (0.82, 0.75, 0.58), (0.65, 0.30, 0.18)))
    wl('')

    # 3. Academic Block
    wl('# Academic Block')
    wl(build("Academic Block", 22, -22, 16, 12, 7, (0.80, 0.73, 0.56), (0.58, 0.33, 0.18)))
    wl('')

    # 4. CIVE Library
    wl('# CIVE Library')
    wl(build("CIVE Library", 0, -36, 18, 14, 7, (0.84, 0.77, 0.60), (0.55, 0.35, 0.22)))
    wl('')

    # 5. CIVE New Labs
    wl('# CIVE New Labs')
    wl(build("CIVE New Labs", -22, -36, 16, 12, 6, (0.82, 0.75, 0.58), (0.40, 0.50, 0.60)))
    wl('')

    # 6. CIVE Old Labs
    wl('# CIVE Old Labs')
    wl(build("CIVE Old Labs", 22, -36, 16, 12, 6, (0.80, 0.73, 0.56), (0.60, 0.35, 0.20)))
    wl('')

    # 7. LRA Lecture Rooms
    wl('# LRA Lecture Rooms')
    wl(build("LRA Lecture Rooms", -22, -50, 16, 10, 5, (0.82, 0.75, 0.58), (0.40, 0.50, 0.60)))
    wl('')

    # 8. LRB Lecture Rooms
    wl('# LRB Lecture Rooms')
    wl(build("LRB Lecture Rooms", 22, -50, 16, 10, 5, (0.80, 0.73, 0.56), (0.58, 0.33, 0.18)))
    wl('')

    # ===== STUDENT SERVICES =====
    wl('# ======= STUDENT SERVICES =======')
    wl('')

    # 9. CIVE Cafeteria
    wl('# CIVE Cafeteria')
    wl(build("CIVE Cafeteria", 0, -46, 18, 10, 4, (0.85, 0.78, 0.62), (0.62, 0.38, 0.22)))
    wl('')

    # 10. CIVE Dispensary
    wl('# CIVE Dispensary')
    wl(build("CIVE Dispensary", -22, -62, 10, 8, 3, (0.90, 0.82, 0.65), (0.70, 0.35, 0.20)))
    wl('')

    # ===== STUDENT HOSTELS (Blocks 1-6) =====
    wl('# ======= STUDENT HOSTELS (Blocks 1-6) =======')
    wl('')

    # Blocks on western side
    block_roof = (0.55, 0.30, 0.15)
    for i, (bx, by) in enumerate([(-10, -62), (-10, -70), (-10, -78)], 1):
        wl(build(f"Block {i}", bx, by, 12, 8, 6, (0.82, 0.75, 0.58), block_roof))
    wl('')

    # Blocks on eastern side
    for i, (bx, by) in enumerate([(10, -62), (10, -70), (10, -78)], 4):
        wl(build(f"Block {i}", bx, by, 12, 8, 6, (0.80, 0.73, 0.56), block_roof))
    wl('')

    # ===== BENJAMIN MKAPA BUILDING (landmark, central admin) =====
    wl('# Benjamin Mkapa Building (landmark)')
    wl('SimpleBuilding {')
    wl('  translation -55 -60 0')
    wl('  name "Benjamin Mkapa Building"')
    wl('  enableBoundingObject FALSE')
    wl('}')
    wl('')

    # ===== ROADS =====
    wl('# ======= ROADS =======')
    wl('')

    # Main road (Ujasi Road - dirt, N-S)
    wl('# Ujasi Road (main access, dirt surface)')
    wl('Road { translation 0 0 0.01 width 6 numberOfLanes 2')
    wl('  rightBorder TRUE leftBorder TRUE')
    wl('  wayPoints [0 -55 0, 2 -15 0, 0 55 0]')
    wl('  splineSubdivision 4')
    wl('  appearance Pavement { type "black stone" }')
    wl('}')
    wl('')

    # Block 2/3 Road (asphalt, connects hostels)
    wl('# Block 2/3 Road (asphalt, excellent)')
    wl('Road { translation 0 0 0.01 width 5 numberOfLanes 2')
    wl('  rightBorder TRUE leftBorder TRUE')
    wl('  wayPoints [0 -55 0, 0 -85 0]')
    wl('  splineSubdivision 4')
    wl('  appearance Pavement { type "black stone" }')
    wl('}')
    wl('')

    # East-West connector road
    wl('# East-West connector')
    wl('Road { translation 0 0 0.01 width 5 numberOfLanes 2')
    wl('  rightBorder TRUE leftBorder TRUE')
    wl('  wayPoints [-30 -22 0, 30 -22 0]')
    wl('  splineSubdivision 4')
    wl('  appearance Pavement { type "black stone" }')
    wl('}')
    wl('')

    # Path to library/labs
    wl('# Access path to library & labs')
    wl('Road { translation 0 0 0.01 width 4 numberOfLanes 1')
    wl('  rightBorder FALSE leftBorder FALSE')
    wl('  wayPoints [-30 -36 0, 30 -36 0]')
    wl('  splineSubdivision 4')
    wl('  appearance Pavement { type "black stone" }')
    wl('}')
    wl('')

    # ===== PARKING =====
    wl('# Parking near admin')
    wl('Floor { translation 0 -16 0.01 size 20 8')
    wl('  appearance Asphalt {}')
    wl('}')
    wl('')

    # ===== PEDESTRIAN WALKWAYS =====
    wl('# ======= PEDESTRIAN WALKWAYS =======')
    wl('')
    wl('# Plaza between Admin & Library')
    wl('Floor { translation 0 -29 0.015 size 10 10')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('')
    wl('# North-South walkway from Admin to Library plaza')
    wl('Floor { translation 0 -25.5 0.015 size 4 8')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('')
    wl('# Walkway from Library plaza to Cafeteria')
    wl('Floor { translation 0 -41 0.015 size 4 8')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('')
    wl('# Walkway from Academic buildings to Labs/Library')
    wl('Floor { translation -22 -29 0.015 size 4 12')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('Floor { translation 22 -29 0.015 size 4 12')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('')
    wl('# Walkway from Labs area to Lecture rooms')
    wl('Floor { translation -22 -43 0.015 size 4 12')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('Floor { translation 22 -43 0.015 size 4 12')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('')
    wl('# Walkway from main path to hostels')
    wl('Floor { translation 0 -56 0.015 size 6 6')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('')
    wl('# Hostel internal walkway')
    wl('Floor { translation -10 -70 0.015 size 14 4')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('Floor { translation 10 -70 0.015 size 14 4')
    wl('  appearance Pavement { type "gray stone" }')
    wl('}')
    wl('')

    # ===== VEGETATION =====
    wl('# ======= VEGETATION =======')
    wl('')

    # Acacia trees along roads and around buildings
    trees = [
        # Along Ujasi Road (main)
        (-8, -10), (8, -10), (-8, -6), (8, -6),
        (-6, -55), (6, -55), (-8, -60), (8, -60),
        # Around admin
        (-14, -18), (14, -18), (-14, -26), (14, -26),
        # Around library
        (-12, -32), (12, -32), (-12, -40), (12, -40),
        # Between academic buildings
        (-10, -22), (-10, -30), (-10, -36), (-10, -44),
        (10, -22), (10, -30), (10, -36), (10, -44),
        # Near auditorium
        (-28, -18), (-28, -26), (-28, -30), (-28, -40),
        # Near hostels
        (-4, -62), (4, -62), (-4, -70), (4, -70),
        (-4, -78), (4, -78), (-16, -66), (-16, -74),
        (16, -66), (16, -74),
        # Along east-west roads
        (-26, -50), (26, -50), (-26, -22), (26, -22),
        # Scattered
        (-6, -88), (6, -88), (0, -92),
        (-20, -84), (20, -84),
    ]
    for tx, ty in trees:
        h = round(5 + math.sin(tx * 1.7 + ty * 0.9) * 3, 1)
        cr = round(3 + math.cos(tx * 0.5 + ty * 0.3) * 1.5, 1)
        wl(f'AcaciaTree {{ translation {tx} {ty} 0 name "tree" height {h} canopyRadius {cr} }}')
    wl('')

    # A few Pine trees for variety
    pines = [(-30, -14), (30, -14), (-30, -42), (30, -42), (0, -50), (0, -86)]
    for px, py in pines:
        wl(f'Pine {{ translation {px} {py} 0 enableBoundingObject FALSE }}')
    wl('')

    # ===== CARS =====
    wl('# Cars in parking')
    for cx, cy in [(-4, -16), (0, -16), (4, -16), (-6, -18), (6, -18), (-2, -18), (2, -18)]:
        wl(f'TeslaModel3Simple {{ translation {cx} {cy} 0.31 name "car" }}')
    wl('')

    # ===== TRAFFIC CONES =====
    wl('# Traffic cones')
    for cx, cy in [(-3, -55), (3, -55), (-2, -15), (2, -15)]:
        wl(f'TrafficCone {{ translation {cx} {cy} 0 physics NULL }}')
    wl('')

    # ===== DRONE =====
    if include_drone:
        wl('# Mavic 2 Pro Drone')
        wl('Mavic2Pro {')
        wl('  translation 2 -15 0.070')
        wl('  rotation 0 0 1 0')
        wl('  controller "px4_bridge"')
        wl('  cameraSlot [ Camera { width 640 height 480 near 0.2 } ]')
        wl('}')
        wl('')

    content = '\n'.join(lines)
    with open(output_path, 'w') as f:
        f.write(content)
    print(f"Generated: {output_path}")
    print(f"  Buildings: 8 academic + 6 hostels + cafeteria + dispensary")
    print(f"  Trees: {len(trees)} Acacia + {len(pines)} Pine")
    print(f"  Cars: 7")
    return content


def main():
    parser = argparse.ArgumentParser(description="Generate UDOM CIVE Campus Webots world")
    parser.add_argument("--output", default=None)
    parser.add_argument("--no-drone", action="store_true")
    args = parser.parse_args()

    if args.output is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(script_dir, "..", "..", "webots", "worlds", "dodoma_tanzania.wbt")
    else:
        output_path = args.output

    generate_world(output_path, include_drone=not args.no_drone)
    print()
    print("Run: ./start_webots.sh")
    print()


if __name__ == "__main__":
    main()
